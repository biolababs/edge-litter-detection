from __future__ import annotations

import argparse
import os


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Serve single-image litter detection over HTTP."
    )
    parser.add_argument(
        "--host",
        default=os.environ.get("LITTER_HOST", "127.0.0.1"),
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.environ.get("LITTER_PORT", "8088")),
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    if not 1 <= args.port <= 65535:
        raise SystemExit("--port must be between 1 and 65535.")
    try:
        import uvicorn
    except ImportError as exc:
        raise RuntimeError(
            "Uvicorn is missing. Install the 'api' optional dependency."
        ) from exc
    uvicorn.run(
        "litter_edge.api:app",
        host=args.host,
        port=args.port,
        workers=1,
    )


if __name__ == "__main__":
    main()
