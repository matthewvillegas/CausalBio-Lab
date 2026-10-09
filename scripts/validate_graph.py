"""Validate every discovered domain pack and report provenance/freshness diagnostics."""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from datetime import date
from pathlib import Path

from causalbio.demo.integrity import validate_domain_pack
from causalbio.demo.registry import DomainPackRegistry


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pack-root", type=Path, help="Directory containing <slug>/pack.json")
    parser.add_argument(
        "--as-of", type=date.fromisoformat, help="Fixed YYYY-MM-DD for freshness checks"
    )
    args = parser.parse_args(argv)
    registry = DomainPackRegistry(args.pack_root)
    try:
        slugs = registry.slugs()
        if not slugs:
            raise ValueError("No domain packs were discovered")
        results = []
        for slug in slugs:
            pack = registry.load(slug)
            graph = validate_domain_pack(pack)
            results.append(
                {
                    "slug": slug,
                    "version": pack.version,
                    "valid": True,
                    **graph.integrity_summary(as_of=args.as_of),
                }
            )
        print(json.dumps({"packs": results}, indent=2))
        return 0
    except (ValueError, KeyError, OSError) as exc:
        print(json.dumps({"valid": False, "error": str(exc)}, indent=2))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
