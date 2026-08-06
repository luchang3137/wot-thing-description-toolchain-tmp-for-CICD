"""Helpers to compare the generated spec HTML with the manual golden HTML.

Both files are ReSpec source documents, but they are serialized differently
(the golden is pretty-printed, the generated file is compact), so a plain
text diff only reports formatting noise. The comparison here works on the
parsed DOM instead:

- sections are matched by section id, tables by caption text, table rows
  by their ``tr`` id (or by the first cell text when the table has no row
  ids), so an error message can name the exact term and column
- cell content is reduced to a list of tokens before comparing. Only tags
  that carry meaning for the reader are kept: ``a``, ``code``, ``em``,
  ``strong``, ``cite``. Other tags contribute only their text, and all
  whitespace is collapsed, so serialization differences do not show up
- inside a link only the link text is compared. The golden file leaves many
  links as empty ReSpec autolinks (``<a>Array</a>``) that ReSpec resolves
  at render time, while the generated file ships them already resolved with
  ``href``, extra attributes and ``<code>`` wrappers. The ``href`` is
  compared only when both files state one explicitly.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import lxml.html
from lxml.html import HtmlElement

SEMANTIC_TAGS = {"a", "code", "em", "strong", "cite"}


@dataclass(frozen=True)
class Token:
    """One compared unit of cell content: a text run or a semantic tag."""

    kind: str
    text: str
    href: str | None = None

    def __str__(self) -> str:
        if self.kind == "text":
            return self.text
        if self.kind == "a" and self.href is not None:
            return f'<a href="{self.href}">{self.text}</a>'
        return f"<{self.kind}>{self.text}</{self.kind}>"


def parse_html(path: Path) -> HtmlElement:
    return lxml.html.parse(str(path)).getroot()


def normalize_text(text: str | None) -> str:
    return " ".join((text or "").split())


def section_by_id(tree: HtmlElement, section_id: str) -> HtmlElement | None:
    sections = tree.cssselect(f'section[id="{section_id}"]')
    return sections[0] if sections else None


def heading_texts(section: HtmlElement) -> list[str]:
    return [normalize_text(h.text_content()) for h in section.cssselect("h2, h3, h4")]


def tables_by_caption(section: HtmlElement) -> dict[str, HtmlElement]:
    tables: dict[str, HtmlElement] = {}
    for table in section.cssselect("table"):
        captions = table.cssselect("caption")
        if captions:
            tables[normalize_text(captions[0].text_content())] = table
    return tables


def captionless_tables(section: HtmlElement) -> list[str]:
    """First-row text of every table that has no caption, as a hint for reports."""
    hints = []
    for table in section.cssselect("table"):
        if not table.cssselect("caption"):
            rows = table.cssselect("tr")
            hints.append(normalize_text(rows[0].text_content()) if rows else "(empty)")
    return hints


def _collect_tokens(element: HtmlElement, tokens: list[Token]) -> None:
    if element.text:
        tokens.append(Token("text", element.text))
    for child in element:
        if not isinstance(child.tag, str):
            # skip comment nodes, but keep the text after them
            if child.tail:
                tokens.append(Token("text", child.tail))
            continue
        tag = child.tag.lower()
        if tag == "a":
            tokens.append(Token("a", normalize_text(child.text_content()), child.get("href")))
        elif tag in SEMANTIC_TAGS:
            tokens.append(Token(tag, normalize_text(child.text_content())))
        else:
            _collect_tokens(child, tokens)
        if child.tail:
            tokens.append(Token("text", child.tail))


def cell_tokens(cell: HtmlElement) -> list[Token]:
    """Reduce a table cell to the token list described in the module docstring."""
    raw: list[Token] = []
    _collect_tokens(cell, raw)
    merged: list[Token] = []
    for token in raw:
        if token.kind == "text" and merged and merged[-1].kind == "text":
            merged[-1] = Token("text", merged[-1].text + " " + token.text)
        else:
            merged.append(token)
    normalized = [
        Token(t.kind, normalize_text(t.text), t.href) if t.kind == "text" else t
        for t in merged
    ]
    return [t for t in normalized if t.text]


def tokens_equal(golden: Token, generated: Token) -> bool:
    if golden.kind != generated.kind or golden.text != generated.text:
        return False
    if golden.kind == "a" and golden.href is not None and generated.href is not None:
        return golden.href == generated.href
    return True


def _tokens_repr(tokens: list[Token]) -> str:
    return " ".join(str(t) for t in tokens)


def compare_cells(context: str, golden_cell: HtmlElement, generated_cell: HtmlElement) -> list[str]:
    golden_tokens = cell_tokens(golden_cell)
    generated_tokens = cell_tokens(generated_cell)
    if len(golden_tokens) != len(generated_tokens):
        return [
            f"{context}: cell content differs\n"
            f"    golden:    {_tokens_repr(golden_tokens)}\n"
            f"    generated: {_tokens_repr(generated_tokens)}"
        ]
    findings = []
    for position, (golden_token, generated_token) in enumerate(zip(golden_tokens, generated_tokens)):
        if not tokens_equal(golden_token, generated_token):
            findings.append(
                f"{context}: token {position} differs - "
                f"golden {golden_token} | generated {generated_token}"
            )
    return findings


def table_rows(table: HtmlElement) -> list[HtmlElement]:
    body_rows = table.cssselect("tbody tr")
    if body_rows:
        return body_rows
    return [row for row in table.cssselect("tr") if row.cssselect("td")]


def row_key(row: HtmlElement) -> str:
    if row.get("id"):
        return row.get("id")
    cells = row.cssselect("td")
    return normalize_text(cells[0].text_content()) if cells else "(empty row)"


def compare_tables(context: str, golden_table: HtmlElement, generated_table: HtmlElement) -> list[str]:
    findings = []

    golden_headers = [normalize_text(th.text_content()) for th in golden_table.cssselect("th")]
    generated_headers = [normalize_text(th.text_content()) for th in generated_table.cssselect("th")]
    if golden_headers != generated_headers:
        findings.append(
            f"{context}: header row differs - golden {golden_headers} | generated {generated_headers}"
        )

    golden_rows = {row_key(r): r for r in table_rows(golden_table)}
    generated_rows = {row_key(r): r for r in table_rows(generated_table)}
    for key in golden_rows.keys() - generated_rows.keys():
        findings.append(f"{context}: row '{key}' is in the golden but not in the generated file")
    for key in generated_rows.keys() - golden_rows.keys():
        findings.append(f"{context}: row '{key}' is in the generated but not in the golden file")

    golden_order = [k for k in golden_rows if k in generated_rows]
    generated_order = [k for k in generated_rows if k in golden_rows]
    if golden_order != generated_order:
        findings.append(f"{context}: rows are in a different order")

    for key in golden_order:
        golden_cells = golden_rows[key].cssselect("td")
        generated_cells = generated_rows[key].cssselect("td")
        if len(golden_cells) != len(generated_cells):
            findings.append(
                f"{context}, row '{key}': {len(golden_cells)} cells in golden, "
                f"{len(generated_cells)} in generated"
            )
            continue
        for column, (golden_cell, generated_cell) in enumerate(zip(golden_cells, generated_cells)):
            findings.extend(
                compare_cells(f"{context}, row '{key}', column {column}", golden_cell, generated_cell)
            )
    return findings


def assertion_texts(tree: HtmlElement) -> dict[str, str]:
    """Map assertion span id -> normalized plain text (markup is not compared here)."""
    spans = tree.cssselect("span.rfc2119-assertion[id]")
    return {span.get("id"): normalize_text(span.text_content()) for span in spans}


def duplicate_ids(section: HtmlElement) -> list[str]:
    seen: set[str] = set()
    duplicates = []
    for element in section.cssselect("[id]"):
        element_id = element.get("id")
        if element_id in seen:
            duplicates.append(element_id)
        seen.add(element_id)
    return duplicates
