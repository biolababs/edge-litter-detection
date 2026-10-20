from __future__ import annotations

import os


def main() -> None:
    try:
        import uvicorn
    except ImportError as exc:
        raise RuntimeError(
            "Uvicorn is missing. Install the 'api' optional dependency."
        ) from exc
    uvicorn.run(
        "litter_edge.api:app",
        host=os.environ.get("LITTER_HOST", "127.0.0.1"),
        port=int(os.environ.get("LITTER_PORT", "8088")),
        workers=1,
    )


if __name__ == "__main__":
    main()
