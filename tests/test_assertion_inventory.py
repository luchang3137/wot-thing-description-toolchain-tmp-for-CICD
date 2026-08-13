"""Compare our assertion inventory with the upstream one.

Upstream (w3c/wot-thing-description) builds testing/assertions.csv from two
files: index.html and testing/inputs/extra-asserts.html. We do the same in
html_assertions_to_csv (src/wotis/specgen/assertions.py) and we feed it a copy
of the upstream extra-asserts.html, so both inventories are built the same way.

That our CSV matches our own HTML is already checked during generation by
validate_html_assertion_inventory, which stops the run when they disagree. What
is left is the comparison with upstream, and that is what this file does.

This test only reports, it does not fail on a difference. Our spec is TD 2.0
and the upstream one is TD 1.1, so some assertions are expected to differ. The
numbers go out as a warning so they stay visible in the test output.
"""
from __future__ import annotations

import csv
import warnings
from pathlib import Path

import pytest

TESTS_DIR = Path(__file__).resolve().parent
REPO_ROOT = TESTS_DIR.parent
OUR_CSV = REPO_ROOT / "resources" / "gens" / "assertions" / "assertions.csv"
UPSTREAM_CSV = REPO_ROOT / "resources" / "upstream" / "assertions.csv"


def assertion_ids(path: Path) -> set[str]:
    with path.open(newline="", encoding="utf-8") as fh:
        return {row["ID"] for row in csv.DictReader(fh) if row.get("ID")}


def test_assertion_ids_vs_upstream() -> None:
    if not OUR_CSV.exists():
        pytest.skip(f"Assertion CSV not found at {OUR_CSV}; run `wotis generate-wot-resources -d` first.")

    ours = assertion_ids(OUR_CSV)
    upstream = assertion_ids(UPSTREAM_CSV)
    assert ours, "our assertion inventory is empty"
    assert upstream, "upstream assertion inventory is empty"

    missing = sorted(upstream - ours)
    extra = sorted(ours - upstream)
    if not missing and not extra:
        return

    warnings.warn(
        f"assertion ids differ from upstream: {len(ours)} ours, {len(upstream)} upstream, "
        f"{len(ours & upstream)} in both\n"
        f"  in upstream but not here ({len(missing)}): {', '.join(missing) or '-'}\n"
        f"  here but not in upstream ({len(extra)}): {', '.join(extra) or '-'}",
        stacklevel=2,
    )
