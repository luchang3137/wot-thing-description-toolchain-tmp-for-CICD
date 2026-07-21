"""TD-instance gate.

The generated JSON Schema must accept every ``*-valid`` sample and reject every
``*-invalid`` one, for both TD 1.1 and TD 2.0. Valid samples the schema wrongly
rejects (known fidelity gaps) are listed in the per-version known-failures files
and marked xfail(strict): a fix that makes one pass forces removing it there, so
the list can only shrink.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import validators
from jsonschema.exceptions import best_match

from .baselines import load_baseline

TESTS_DIR = Path(__file__).resolve().parent
REPO_ROOT = TESTS_DIR.parent
SCHEMA_PATH = REPO_ROOT / "resources" / "gens" / "jsonschema" / "jsonschema.json"

TD_VERSIONS = [
    ("td11", TESTS_DIR / "data" / "td11", TESTS_DIR / "td_gate_known_failures_td11.txt"),
    ("td20", TESTS_DIR / "data" / "td20", TESTS_DIR / "td_gate_known_failures_td20.txt"),
]


@pytest.fixture(scope="session")
def validator():
    if not SCHEMA_PATH.exists():
        pytest.skip(f"Generated schema not found at {SCHEMA_PATH}; run `wotis generate-wot-resources` first.")
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    cls = validators.validator_for(schema)
    cls.check_schema(schema)
    return cls(schema)


def _samples():
    params = []
    for version, data_dir, failures_file in TD_VERSIONS:
        if not data_dir.exists():
            continue
        known_failures = load_baseline(failures_file)
        for path in sorted(data_dir.rglob("*.jsonld")):
            rel = path.relative_to(data_dir).as_posix()
            marks = [pytest.mark.xfail(strict=True, reason="known fidelity gap")] if rel in known_failures else []
            params.append(pytest.param(path, id=f"{version}/{rel}", marks=marks))
    return params


@pytest.mark.parametrize("td_path", _samples())
def test_td_instance(validator, td_path: Path):
    expected_valid = "invalid" not in td_path.name.lower()
    instance = json.loads(td_path.read_text(encoding="utf-8"))
    error = best_match(validator.iter_errors(instance))
    if expected_valid:
        assert error is None, f"expected VALID but schema rejected {td_path.name}: {error and error.message}"
    else:
        assert error is not None, f"expected INVALID but schema accepted {td_path.name}"


def _baselines():
    params = []
    for version, data_dir, failures_file in TD_VERSIONS:
        entries = load_baseline(failures_file)
        if entries:
            params.append(pytest.param(data_dir, entries, id=version))
    return params


@pytest.mark.parametrize("data_dir, known_failures", _baselines())
def test_known_failures_are_valid_samples(data_dir: Path, known_failures):
    bad = sorted(p for p in known_failures if "invalid" in Path(p).name.lower())
    assert not bad, f"known-failures must list only valid samples, found: {bad}"


@pytest.mark.parametrize("data_dir, known_failures", _baselines())
def test_known_failures_paths_exist(data_dir: Path, known_failures):
    missing = sorted(p for p in known_failures if not (data_dir / p).exists())
    assert not missing, f"known-failures entries no longer exist: {missing}"
