"""Check whether upstream files we copied or derived from got new commits.

Reads resources/upstream-sources.json. For every tracked entry it asks the
GitHub API for the newest commit that touched the upstream path. If that
commit is not the recorded last_synced_commit, the file needs a human review.
Entries with sync "copy" are also compared by content. All entries are
checked first, then the script fails once with the full list of findings.

After reviewing and syncing a file, update its last_synced_commit in the
manifest to make this check green again.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = REPO_ROOT / "resources" / "upstream-sources.json"
API_BASE = "https://api.github.com"
RAW_BASE = "https://raw.githubusercontent.com"


def request_headers() -> dict[str, str]:
    token = os.environ.get("GITHUB_TOKEN", "")
    if not token:
        return {}
    return {"Authorization": f"Bearer {token}"}


def fetch_json(url: str) -> object:
    request = urllib.request.Request(url, headers=request_headers())
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


def fetch_bytes(url: str) -> bytes:
    request = urllib.request.Request(url, headers=request_headers())
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read()


def latest_upstream_commit(repo: str, path: str) -> dict[str, str]:
    url = f"{API_BASE}/repos/{repo}/commits?path={path}&per_page=1"
    commits = fetch_json(url)
    if not isinstance(commits, list) or not commits:
        raise RuntimeError(f"no upstream commits found for {path}")
    newest = commits[0]
    return {
        "sha": newest["sha"],
        "date": newest["commit"]["committer"]["date"],
        "message": newest["commit"]["message"].splitlines()[0],
    }


def check_entry(repo: str, entry: dict[str, str]) -> list[str]:
    findings: list[str] = []
    newest = latest_upstream_commit(repo, entry["upstream_path"])
    if newest["sha"] != entry["last_synced_commit"]:
        findings.append(
            f"{entry['local']}: upstream {entry['upstream_path']} has new commit "
            f"{newest['sha'][:8]} ({newest['date']}, \"{newest['message']}\"), "
            f"last synced at {entry['last_synced_commit'][:8]}"
        )
    if entry["sync"] == "copy":
        upstream_bytes = fetch_bytes(
            f"{RAW_BASE}/{repo}/{newest['sha']}/{entry['upstream_path']}"
        )
        local_bytes = (REPO_ROOT / entry["local"]).read_bytes()
        if hashlib.sha256(upstream_bytes).digest() != hashlib.sha256(local_bytes).digest():
            findings.append(
                f"{entry['local']}: content differs from upstream "
                f"{entry['upstream_path']} at {newest['sha'][:8]}"
            )
    return findings


def write_step_summary(lines: list[str]) -> None:
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY", "")
    if not summary_path:
        return
    with open(summary_path, "a", encoding="utf-8") as summary:
        summary.write("## Upstream sync check\n\n")
        for line in lines:
            summary.write(f"- {line}\n")


def main() -> int:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    repo = manifest["upstream_repo"]
    findings: list[str] = []
    for entry in manifest["files"]:
        if entry["sync"] == "frozen":
            continue
        findings.extend(check_entry(repo, entry))
    if not findings:
        print("all tracked upstream files are unchanged since the last sync")
        return 0
    print(f"{len(findings)} upstream file(s) need review:")
    for finding in findings:
        print(f"- {finding}")
    write_step_summary(findings)
    return 1


if __name__ == "__main__":
    sys.exit(main())
