from __future__ import annotations

import argparse
import hashlib
import os
import re
import tempfile
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlsplit, urlunsplit
from urllib.request import Request, urlopen

from .common import utc_now, write_json


SHA256_PATTERN = re.compile(r"^[0-9a-fA-F]{64}$")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Download a trained litter checkpoint and verify its SHA-256."
    )
    parser.add_argument("--url", required=True, help="HTTPS model artifact URL.")
    parser.add_argument("--sha256", required=True, help="Expected SHA-256 digest.")
    parser.add_argument(
        "--output",
        default="models/rfdetr-nano-litter.pth",
    )
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument(
        "--max-bytes",
        type=int,
        default=2 * 1024 * 1024 * 1024,
        help="Maximum accepted download size.",
    )
    parser.add_argument("--force", action="store_true")
    return parser


def _safe_url(value: str) -> str:
    parsed = urlsplit(value)
    if parsed.scheme.lower() != "https":
        raise ValueError("Model downloads require an HTTPS URL.")
    if not parsed.hostname:
        raise ValueError("Model URL must include a hostname.")
    hostname = parsed.hostname
    if ":" in hostname and not hostname.startswith("["):
        hostname = f"[{hostname}]"
    authority = f"{hostname}:{parsed.port}" if parsed.port else hostname
    return urlunsplit((parsed.scheme, authority, parsed.path, "", ""))


def download_model(
    *,
    url: str,
    expected_sha256: str,
    output: str | Path,
    timeout: float = 30.0,
    max_bytes: int = 2 * 1024 * 1024 * 1024,
    force: bool = False,
    opener: Callable[..., Any] = urlopen,
) -> dict[str, Any]:
    safe_url = _safe_url(url)
    if not SHA256_PATTERN.fullmatch(expected_sha256):
        raise ValueError("sha256 must contain exactly 64 hexadecimal characters.")
    if timeout <= 0:
        raise ValueError("timeout must be positive.")
    if max_bytes <= 0:
        raise ValueError("max_bytes must be positive.")

    destination = Path(output)
    if destination.exists() and not force:
        raise FileExistsError(
            f"Model already exists: {destination}. Pass --force to replace it."
        )
    destination.parent.mkdir(parents=True, exist_ok=True)

    request = Request(url, headers={"User-Agent": "edge-litter-detection/0.6"})
    temporary_path: Path | None = None
    digest = hashlib.sha256()
    downloaded_bytes = 0
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            prefix=f".{destination.name}.",
            suffix=".download",
            dir=destination.parent,
            delete=False,
        ) as temporary:
            temporary_path = Path(temporary.name)
            with opener(request, timeout=timeout) as response:
                content_length = response.headers.get("Content-Length")
                if content_length and int(content_length) > max_bytes:
                    raise ValueError("Model artifact exceeds max_bytes.")
                while chunk := response.read(1024 * 1024):
                    downloaded_bytes += len(chunk)
                    if downloaded_bytes > max_bytes:
                        raise ValueError("Model artifact exceeds max_bytes.")
                    temporary.write(chunk)
                    digest.update(chunk)

        observed_sha256 = digest.hexdigest()
        if observed_sha256.lower() != expected_sha256.lower():
            raise ValueError(
                "Model checksum mismatch: "
                f"expected {expected_sha256.lower()}, observed {observed_sha256}."
            )
        os.replace(temporary_path, destination)
        temporary_path = None
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)

    manifest = {
        "created_at": utc_now(),
        "operation": "download_model",
        "source": safe_url,
        "output": str(destination),
        "sha256": expected_sha256.lower(),
        "bytes": downloaded_bytes,
    }
    manifest_path = destination.with_suffix(destination.suffix + ".download.json")
    write_json(manifest_path, manifest)
    return manifest


def main() -> None:
    args = build_parser().parse_args()
    manifest = download_model(
        url=args.url,
        expected_sha256=args.sha256,
        output=args.output,
        timeout=args.timeout,
        max_bytes=args.max_bytes,
        force=args.force,
    )
    print(f"Verified model: {manifest['output']}")
    print(f"SHA-256: {manifest['sha256']}")


if __name__ == "__main__":
    main()
