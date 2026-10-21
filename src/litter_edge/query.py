from __future__ import annotations

import argparse
import json

from .storage import (
    list_outbox_events,
    list_review_queue,
    list_runs,
    summarize_counts,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Query persisted litter observations from the local SQLite store."
    )
    parser.add_argument(
        "command",
        nargs="?",
        choices=("summary", "runs", "reviews", "outbox"),
        default="summary",
    )
    parser.add_argument(
        "--database",
        default="state/litter-edge.db",
    )
    parser.add_argument("--vehicle-id")
    parser.add_argument("--route-id")
    parser.add_argument("--edge-device-id")
    parser.add_argument("--status", default="pending")
    parser.add_argument("--limit", type=int, default=50)
    parser.add_argument("--include-acknowledged", action="store_true")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    if args.command == "summary":
        payload = summarize_counts(
            args.database,
            vehicle_id=args.vehicle_id,
            route_id=args.route_id,
            edge_device_id=args.edge_device_id,
        )
    elif args.command == "runs":
        payload = {
            "runs": list_runs(
                args.database,
                limit=args.limit,
                vehicle_id=args.vehicle_id,
                route_id=args.route_id,
                edge_device_id=args.edge_device_id,
            )
        }
    elif args.command == "reviews":
        payload = {
            "reviews": list_review_queue(
                args.database,
                status=args.status,
                limit=args.limit,
            )
        }
    else:
        payload = {
            "events": list_outbox_events(
                args.database,
                limit=args.limit,
                include_acknowledged=args.include_acknowledged,
            )
        }
    print(json.dumps(payload, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
