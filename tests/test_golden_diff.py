"""Golden diff: the generated JSON artifacts must match the committed snapshots
under tests/goldens/. If a change is intended, update the snapshots with:

    uv run pytest tests/test_golden_diff.py --update-goldens
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

TESTS_DIR = Path(__file__).resolve().parent
REPO_ROOT = TESTS_DIR.parent
GOLDENS_DIR = TESTS_DIR / "goldens"

ARTIFACTS = [
    ("jsonschema.json", REPO_ROOT / "resources" / "gens" / "jsonschema" / "jsonschema.json"),
    ("context.jsonld", REPO_ROOT / "resources" / "gens" / "jsonldcontext" / "context.jsonld"),
]


def _normalize(path: Path) -> str:
    data = json.loads(path.read_text(encoding="utf-8"))
    return json.dumps(data, sort_keys=True, indent=2, ensure_ascii=False) + "\n"


@pytest.mark.parametrize("name, gen_path", ARTIFACTS, ids=[n for n, _ in ARTIFACTS])
def test_golden_matches_generated(request, name: str, gen_path: Path):
    if not gen_path.exists():
        pytest.skip(f"Generated artifact not found: {gen_path}")
    current = _normalize(gen_path)
    golden_path = GOLDENS_DIR / name

    if request.config.getoption("--update-goldens"):
        GOLDENS_DIR.mkdir(parents=True, exist_ok=True)
        golden_path.write_text(current, encoding="utf-8")
        pytest.skip(f"Golden updated: {golden_path}")

    assert golden_path.exists(), f"Golden missing: {golden_path}; run with --update-goldens to create it."
    assert current == golden_path.read_text(encoding="utf-8"), (
        f"Generated {name} differs from the golden snapshot; if intended, update with --update-goldens."
    )
