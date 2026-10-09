"""Enumerate publication candidates, including an uncommitted first release."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def public_files() -> list[Path]:
    top = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"], cwd=ROOT, capture_output=True, text=True
    )
    if top.returncode == 0 and Path(top.stdout.strip()).resolve() == ROOT:
        result = subprocess.run(
            ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
            cwd=ROOT,
            check=True,
            capture_output=True,
        )
        names = result.stdout.decode("utf-8").split("\0")
    else:
        manifest = ROOT / "artifacts/public-file-manifest.json"
        if not manifest.exists():
            raise SystemExit("Run in the Git checkout or a copy made by create-clean-copy.mjs.")
        names = json.loads(manifest.read_text(encoding="utf-8"))
    paths = sorted({ROOT / name for name in names if name})
    for path in paths:
        if not path.resolve().is_relative_to(ROOT) or path.is_symlink():
            raise SystemExit("Publication candidates must be regular files inside the repository.")
        if not path.is_file():
            raise SystemExit(f"Missing publication candidate: {path.relative_to(ROOT)}")
    return paths
