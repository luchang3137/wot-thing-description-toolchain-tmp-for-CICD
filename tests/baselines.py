from pathlib import Path


def load_baseline(path: Path) -> set[str]:
    """Read a known-failure list: one entry per line, '#' comments ignored."""
    if not path.exists():
        return set()
    entries = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            entries.add(line.split()[0])
    return entries
