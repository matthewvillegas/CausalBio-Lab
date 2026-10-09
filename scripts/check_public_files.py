"""Check the public candidate set without printing suspected credential values."""

from __future__ import annotations

import re
from pathlib import Path

from public_files import ROOT, public_files

PATTERNS = {
    "private user path": re.compile(
        r"(?:[A-Z]:[\\/]Users[\\/][\w .-]+|(?<![\w.:/])/(?:Users|home)/[\w.-]+/)", re.I
    ),
    "private key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "GitHub token": re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,})\b"),
    "AWS access key": re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b"),
    "service key": re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{35,}\b"),
    "personal email": re.compile(r"\b[\w.+-]+@(?:gmail|outlook|hotmail|yahoo)\.com\b", re.I),
}
GENERATED = {
    "node_modules",
    ".next",
    ".venv",
    "__pycache__",
    ".git",
    "test-results",
    "playwright-report",
}
BINARY = {".png", ".jpg", ".webp", ".ico", ".npz", ".mp4", ".webm", ".pdf"}


def problems(path: Path) -> list[str]:
    relative = path.relative_to(ROOT)
    errors = []
    if GENERATED.intersection(relative.parts):
        errors.append("generated dependency/build directory")
    if path.name.startswith(".env") and path.name != ".env.example":
        errors.append("private environment file")
    if re.search(r"\.(?:sqlite3?|db)(?:-(?:wal|shm|journal))?$|\.log$|\.tsbuildinfo$", path.name):
        errors.append("local database/log/build state")
    if path.stat().st_size > 10_000_000:
        errors.append("file exceeds 10 MB publication review threshold")
    if path.suffix.lower() not in BINARY:
        content = path.read_text(encoding="utf-8")
        for label, pattern in PATTERNS.items():
            if pattern.search(content):
                errors.append(label)
    return errors


def main() -> int:
    files = public_files()
    findings = [
        (path.relative_to(ROOT).as_posix(), issue) for path in files for issue in problems(path)
    ]
    for path, issue in findings:
        print(f"REVIEW {path}: {issue}; value withheld")
    print(f"Public-file check: {len(files)} files; {len(findings)} findings.")
    print("Pattern checks supplement manual review; they do not prove absence of every secret.")
    return bool(findings)


if __name__ == "__main__":
    raise SystemExit(main())
