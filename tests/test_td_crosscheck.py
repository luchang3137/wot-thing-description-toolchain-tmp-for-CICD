"""Cross-check the generated schema against the W3C ground-truth schemas.

For every sample, the generated schema's accept/reject verdict must match the
ground-truth schema's. Known divergences are listed per version and marked
xfail(strict), so the list can only shrink.
"""
from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import pytest
from jsonschema import validators

from .baselines import load_baseline

TESTS_DIR = Path(__file__).resolve().parent
REPO_ROOT = TESTS_DIR.parent
SCHEMA_PATH = REPO_ROOT / "resources" / "gens" / "jsonschema" / "jsonschema.json"
GROUND_TRUTH = REPO_ROOT / "resources" / "ground-truth-schemas"

CONFIGS = [
    ("td11", TESTS_DIR / "data" / "td11", GROUND_TRUTH / "td11-json-schema-validation.json",
     TESTS_DIR / "td_crosscheck_known_divergences_td11.txt"),
    ("td20", TESTS_DIR / "data" / "td20", GROUND_TRUTH / "td20-json-schema-validation.json",
     TESTS_DIR / "td_crosscheck_known_divergences_td20.txt"),
]


def _make_validator(schema_path: Path):
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    cls = validators.validator_for(schema)
    cls.check_schema(schema)
    return cls(schema)


def _accepts(validator, instance) -> bool:
    try:
        validator.validate(instance)
        return True
    except jsonschema.ValidationError:
        return False


def _samples():
    params = []
    for version, data_dir, golden_path, divergences_file in CONFIGS:
        if not data_dir.exists() or not golden_path.exists():
            continue
        known = load_baseline(divergences_file)
        for path in sorted(data_dir.rglob("*.jsonld")):
            rel = path.relative_to(data_dir).as_posix()
            marks = [pytest.mark.xfail(strict=True, reason="known divergence from W3C schema")] if rel in known else []
            params.append(pytest.param(path, golden_path, id=f"{version}/{rel}", marks=marks))
    return params


@pytest.fixture(scope="session")
def generated_validator():
    if not SCHEMA_PATH.exists():
        pytest.skip("Generated schema not found; run `wotis generate-wot-resources` first.")
    return _make_validator(SCHEMA_PATH)


@pytest.fixture(scope="session")
def golden_validators():
    cache: dict[Path, object] = {}

    def get(path: Path):
        if path not in cache:
            cache[path] = _make_validator(path)
        return cache[path]

    return get


@pytest.mark.parametrize("td_path, golden_path", _samples())
def test_generated_agrees_with_ground_truth(generated_validator, golden_validators, td_path: Path, golden_path: Path):
    instance = json.loads(td_path.read_text(encoding="utf-8"))
    generated = _accepts(generated_validator, instance)
    golden = _accepts(golden_validators(golden_path), instance)
    assert generated == golden, (
        f"verdict mismatch on {td_path.name}: "
        f"generated={'accept' if generated else 'reject'}, golden={'accept' if golden else 'reject'}"
    )
