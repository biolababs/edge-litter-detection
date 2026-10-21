from __future__ import annotations

import argparse
import ipaddress
import os


def _enabled(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in {"1", "true", "yes"}


def validate_bind_host(host: str) -> str:
    normalized = host.strip()
    if not normalized:
        raise ValueError("Server host cannot be empty.")
    if _enabled("LITTER_CONTAINER_INTERNAL_BIND"):
        return normalized
    if normalized.lower() == "localhost":
        return normalized
    try:
        if ipaddress.ip_address(normalized).is_loopback:
            return normalized
    except ValueError:
        pass
    raise ValueError(
        "The unauthenticated API may bind only to a loopback address. "
        "Use an SSH tunnel or authenticated reverse proxy for remote access. "
        "Container images may set LITTER_CONTAINER_INTERNAL_BIND=true only "
        "when the published host port remains private."
    )


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
        host = validate_bind_host(args.host)
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc
    try:
        import uvicorn
    except ImportError as exc:
        raise RuntimeError(
            "Uvicorn is missing. Install the 'api' optional dependency."
        ) from exc
    uvicorn.run(
        "litter_edge.api:app",
        host=host,
        port=args.port,
        workers=1,
    )


if __name__ == "__main__":
    main()
