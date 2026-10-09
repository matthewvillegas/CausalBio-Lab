"""Review a local candidate file; never mutate curated packs automatically."""

from __future__ import annotations

import argparse
from pathlib import Path
from uuid import UUID

from causalbio.evidence.curation import CandidateDraft, CandidateReviewStore


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, required=True)
    commands = parser.add_subparsers(dest="action", required=True)
    for action in ("submit", "edit", "accept", "reject", "uncertain", "history", "export"):
        command = commands.add_parser(action)
        if action in {"submit", "edit"}:
            command.add_argument("--file", type=Path, required=True)
        else:
            command.add_argument("--id", type=UUID, required=True)
        if action not in {"history", "export"}:
            command.add_argument("--actor", required=True)
            command.add_argument("--reason", required=True)
        if action not in {"submit", "history", "export"}:
            command.add_argument("--revision", type=int, required=True)
        if action == "accept":
            command.add_argument("--confirm-human-review", action="store_true")
    args = parser.parse_args()
    store = CandidateReviewStore(args.database)
    if args.action == "history":
        for event in store.history(args.id):
            print(event.model_dump_json())
    elif args.action == "export":
        print(store.accepted_bundle(args.id).model_dump_json(indent=2))
    elif args.action in {"submit", "edit"}:
        draft = CandidateDraft.model_validate_json(args.file.read_text(encoding="utf-8"))
        if args.action == "submit":
            event = store.submit(draft, actor=args.actor, rationale=args.reason)
        else:
            event = store.edit(
                draft, actor=args.actor, rationale=args.reason, expected_revision=args.revision
            )
        print(event.model_dump_json(indent=2))
    else:
        event = store.review(
            args.id,
            args.action,
            actor=args.actor,
            rationale=args.reason,
            expected_revision=args.revision,
            human_review_confirmed=getattr(args, "confirm_human_review", False),
        )
        print(event.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
