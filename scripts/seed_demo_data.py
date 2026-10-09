"""Validate both curated packs and materialize the local SQLite snapshot."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from pathlib import Path

from causalbio import __version__
from causalbio.demo.registry import domain_pack_slugs, load_domain_pack
from causalbio.evidence.scoring import PathScorer
from causalbio.storage import DEFAULT_DATABASE_PATH, PackSnapshotSummary, SQLiteSnapshotStore

WORKSPACE_ROOT = Path(__file__).resolve().parents[1]


def seed_database(database_path: Path) -> tuple[PackSnapshotSummary, ...]:
    """Load every registry pack and replace its SQLite snapshot."""

    packs = tuple(load_domain_pack(slug) for slug in domain_pack_slugs())
    store = SQLiteSnapshotStore(
        database_path,
        software_version=__version__,
        evidence_rubric_version=PathScorer.rubric_version,
    )
    try:
        return store.replace_packs(packs)
    finally:
        store.dispose()


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate curated domain packs and seed a reproducible SQLite snapshot."
    )
    parser.add_argument(
        "--database",
        type=Path,
        default=WORKSPACE_ROOT / DEFAULT_DATABASE_PATH,
        help="SQLite output path (default: data/causalbio.sqlite3).",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    database_path = args.database.expanduser().resolve()
    summaries = seed_database(database_path)

    print(f"Seeded {len(summaries)} validated domain packs into {database_path}")
    for summary in summaries:
        counts = summary.counts
        provenance = summary.provenance
        print(
            f"- {summary.slug}: entities={counts.entities}, evidence={counts.evidence}, "
            f"assertions={counts.assertions}, hypotheses={counts.hypotheses}, "
            f"interventions={counts.interventions}, petri_models={counts.petri_models}"
        )
        print(
            f"  versions: pack={provenance.pack_version}, graph={provenance.graph_version}, "
            f"schema={provenance.schema_version}, software={provenance.software_version}, "
            f"evidence_rubric={provenance.evidence_rubric_version}, "
            f"petri_model={provenance.petri_model_version}"
        )
        print(f"  content_sha256={provenance.content_sha256}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
