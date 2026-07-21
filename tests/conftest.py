"""Shared test options and the spec-structure known-failures baseline."""
from pathlib import Path

import pytest

from .baselines import load_baseline

TESTS_DIR = Path(__file__).resolve().parent
SPEC_STRUCTURE_BASELINE = TESTS_DIR / "spec_structure_known_failures.txt"


def pytest_addoption(parser):
    parser.addoption(
        "--update-goldens",
        action="store_true",
        help="Overwrite golden files with the current generated output.",
    )


def pytest_collection_modifyitems(config, items):
    """xfail the ReSpec/HTML tests listed in the spec-structure baseline.

    A fix makes a listed test XPASS (strict), which fails until its line is
    removed, so the list can only shrink.
    """
    listed = load_baseline(SPEC_STRUCTURE_BASELINE)
    for item in items:
        if item.nodeid in listed:
            item.add_marker(pytest.mark.xfail(strict=True, reason="known spec-content gap"))
