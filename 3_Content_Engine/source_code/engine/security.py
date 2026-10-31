"""Repository secret scanning with dependency and generated-file exclusions."""
from __future__ import annotations

import re
from pathlib import Path

TEXT_SUFFIXES = {
    ".py", ".json", ".md", ".txt", ".csv", ".toml", ".ini", ".cfg",
    ".yml", ".yaml", ".env", ".ps1", ".bat", ".sh",
}
EXCLUDED_PARTS = {
    ".git", ".venv", "venv", "env", "site-packages", "node_modules",
    "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache", ".tox",
    "dist", "build", "output", "outputs", "2_Main_Output", "evidence",
    "generated_media", ".cache",
}

SECRET_PATTERNS = (
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"\b(?:sk|rk)-[A-Za-z0-9_-]{20,}\b"),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{24,}\b"),
    re.compile(
        r"""(?ix)
        \b(?:api[_-]?key|client[_-]?secret|access[_-]?token|auth[_-]?token|
        password|passwd)\b\s*[:=]\s*["'][^"'\s]{16,}["']
        """
    ),
)


def is_excluded(path: Path, root: Path) -> bool:
    """Return True for virtualenvs, dependencies, caches, and generated output."""
    try:
        parts = path.resolve().relative_to(root.resolve()).parts
    except ValueError:
        return True
    return any(part.lower() in {p.lower() for p in EXCLUDED_PARTS} for part in parts)


def scan_repository(root: Path) -> list[tuple[Path, str]]:
    """Return ``(path, pattern)`` findings from first-party text files only."""
    root = Path(root)
    findings = []
    for path in root.rglob("*"):
        if not path.is_file() or is_excluded(path, root):
            continue
        if path.suffix.lower() not in TEXT_SUFFIXES and not path.name.startswith(".env"):
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for pattern in SECRET_PATTERNS:
            if pattern.search(text):
                findings.append((path, pattern.pattern))
    return findings
