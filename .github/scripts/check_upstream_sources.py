"""Check the files we copied from upstream for updates.

Reads resources/upstream-copies.txt. Every file listed there must stay
identical to its upstream version on the main branch. All files are checked
first, then the script fails once with the full list, so one run shows
everything that needs a sync.
"""
from __future__ import annotations

import hashlib
import sys
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
LIST_PATH = REPO_ROOT / "resources" / "upstream-copies.txt"
UPSTREAM_RAW = "https://raw.githubusercontent.com/w3c/wot-thing-description/main"


def read_list() -> list[tuple[str, str]]:
    """One entry per line, '#' comments ignored: <local path> <upstream path>."""
    entries = []
    for line in LIST_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            local_path, upstream_path = line.split()
            entries.append((local_path, upstream_path))
    return entries


def upstream_digest(upstream_path: str) -> str:
    with urllib.request.urlopen(f"{UPSTREAM_RAW}/{upstream_path}", timeout=30) as response:
        return hashlib.sha256(response.read()).hexdigest()


def main() -> int:
    findings = []
    for local_path, upstream_path in read_list():
        local_digest = hashlib.sha256((REPO_ROOT / local_path).read_bytes()).hexdigest()
        if local_digest != upstream_digest(upstream_path):
            findings.append(f"{local_path} differs from upstream {upstream_path}")

    if not findings:
        print("all copied files are identical to upstream")
        return 0

    print(f"{len(findings)} file(s) differ from upstream:")
    for finding in findings:
        print(f"- {finding}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
