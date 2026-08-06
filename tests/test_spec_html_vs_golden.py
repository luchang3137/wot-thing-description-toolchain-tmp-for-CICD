"""Compare the generated spec HTML against the manual golden HTML.

Scope: the fully auto-generated vocabulary sections (Data Schema, Security,
Hypermedia Controls, Default Values) plus the MultiLanguage subsection. The
golden file tests/manual_goldens/html/index.html is the hand-verified
reference; any difference in these sections is an error.

Every test first walks through everything in its scope and collects all
differences, then fails once with the complete list. There is no known
failures file for these tests on purpose: a difference must either be fixed
in the generator or approved into the golden, not parked.

Link targets are NOT resolved here: both files are ReSpec source documents,
and many anchors (heading ids, #bib-*, #dfn-*) only exist after ReSpec
renders the page. Where both files state an explicit href, the href is
compared by the cell comparison.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from .spec_html_compare import (
    assertion_texts,
    captionless_tables,
    compare_tables,
    duplicate_ids,
    heading_texts,
    normalize_text,
    parse_html,
    section_by_id,
    tables_by_caption,
)

TESTS_DIR = Path(__file__).resolve().parent
REPO_ROOT = TESTS_DIR.parent
GOLDEN_PATH = TESTS_DIR / "manual_goldens" / "html" / "index.html"
GENERATED_PATH = REPO_ROOT / "resources" / "gens" / "index.html"

CONTAINER_SECTION_IDS = [
    "sec-data-schema-vocabulary-definition",
    "sec-security-vocabulary-definition",
    "sec-hypermedia-vocabulary-definition",
    "sec-default-values",
]


@pytest.fixture(scope="module")
def golden_tree():
    if not GOLDEN_PATH.exists():
        pytest.skip(f"Golden HTML not found at {GOLDEN_PATH}")
    return parse_html(GOLDEN_PATH)


@pytest.fixture(scope="module")
def generated_tree():
    if not GENERATED_PATH.exists():
        pytest.skip(f"Generated HTML not found at {GENERATED_PATH}; run `wotis generate-wot-resources -d` first.")
    return parse_html(GENERATED_PATH)


def _sections_or_fail(golden_tree, generated_tree, section_id):
    golden_section = section_by_id(golden_tree, section_id)
    generated_section = section_by_id(generated_tree, section_id)
    assert golden_section is not None, f"section '{section_id}' missing in golden file"
    assert generated_section is not None, f"section '{section_id}' missing in generated file"
    return golden_section, generated_section


def _fail_on_findings(findings: list[str]) -> None:
    assert not findings, f"{len(findings)} difference(s):\n" + "\n".join(findings)


def test_multilanguage_heading_present(golden_tree, generated_tree) -> None:
    for name, tree in [("golden", golden_tree), ("generated", generated_tree)]:
        headings = [normalize_text(h.text_content()) for h in tree.cssselect("h3")]
        assert any(h.endswith("MultiLanguage") for h in headings), (
            f"MultiLanguage heading missing in {name} file"
        )


@pytest.mark.parametrize("section_id", CONTAINER_SECTION_IDS)
def test_section_headings_match(golden_tree, generated_tree, section_id) -> None:
    golden_section, generated_section = _sections_or_fail(golden_tree, generated_tree, section_id)
    golden_headings = heading_texts(golden_section)
    generated_headings = heading_texts(generated_section)
    findings = []
    if golden_headings != generated_headings:
        findings.append(
            f"section '{section_id}': headings differ\n"
            f"    golden:    {golden_headings}\n"
            f"    generated: {generated_headings}"
        )
    _fail_on_findings(findings)


@pytest.mark.parametrize("section_id", CONTAINER_SECTION_IDS)
def test_tables_present_in_both(golden_tree, generated_tree, section_id) -> None:
    golden_section, generated_section = _sections_or_fail(golden_tree, generated_tree, section_id)
    golden_tables = tables_by_caption(golden_section)
    generated_tables = tables_by_caption(generated_section)
    findings = []
    for caption in golden_tables.keys() - generated_tables.keys():
        findings.append(f"section '{section_id}': table '{caption}' missing in generated file")
    for caption in generated_tables.keys() - golden_tables.keys():
        findings.append(f"section '{section_id}': table '{caption}' only in generated file")
    golden_captionless = captionless_tables(golden_section)
    generated_captionless = captionless_tables(generated_section)
    if len(golden_captionless) != len(generated_captionless):
        findings.append(
            f"section '{section_id}': {len(golden_captionless)} captionless table(s) in golden "
            f"(first rows: {golden_captionless}), {len(generated_captionless)} in generated "
            f"(first rows: {generated_captionless})"
        )
    _fail_on_findings(findings)


@pytest.mark.parametrize("section_id", CONTAINER_SECTION_IDS)
def test_table_content_matches(golden_tree, generated_tree, section_id) -> None:
    golden_section, generated_section = _sections_or_fail(golden_tree, generated_tree, section_id)
    golden_tables = tables_by_caption(golden_section)
    generated_tables = tables_by_caption(generated_section)
    findings = []
    for caption in golden_tables:
        if caption not in generated_tables:
            continue  # reported by test_tables_present_in_both
        findings.extend(
            compare_tables(f"table '{caption}'", golden_tables[caption], generated_tables[caption])
        )
    _fail_on_findings(findings)


def test_assertion_spans_match(golden_tree, generated_tree) -> None:
    golden_assertions = assertion_texts(golden_tree)
    generated_assertions = assertion_texts(generated_tree)
    findings = []
    for assertion_id in sorted(golden_assertions.keys() - generated_assertions.keys()):
        findings.append(f"assertion '{assertion_id}' is in the golden but not in the generated file")
    for assertion_id in sorted(generated_assertions.keys() - golden_assertions.keys()):
        findings.append(f"assertion '{assertion_id}' is in the generated but not in the golden file")
    for assertion_id in sorted(golden_assertions.keys() & generated_assertions.keys()):
        if golden_assertions[assertion_id] != generated_assertions[assertion_id]:
            findings.append(
                f"assertion '{assertion_id}': text differs\n"
                f"    golden:    {golden_assertions[assertion_id]}\n"
                f"    generated: {generated_assertions[assertion_id]}"
            )
    _fail_on_findings(findings)


@pytest.mark.parametrize("file_name", ["golden", "generated"])
@pytest.mark.parametrize("section_id", CONTAINER_SECTION_IDS)
def test_no_duplicate_ids(golden_tree, generated_tree, section_id, file_name) -> None:
    tree = golden_tree if file_name == "golden" else generated_tree
    section = section_by_id(tree, section_id)
    assert section is not None, f"section '{section_id}' missing in {file_name} file"
    duplicates = duplicate_ids(section)
    _fail_on_findings([f"{file_name}, section '{section_id}': duplicate id '{d}'" for d in duplicates])
