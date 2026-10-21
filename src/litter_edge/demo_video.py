from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote, urlsplit
from urllib.request import Request, urlopen

from . import __version__


ARCHIVE_IDENTIFIER = "WsdotAdopt-a-highwaySafetyVideo"
ARCHIVE_FILENAME = "WSDOT_Adopt-a-Highway_Safety.mp4"
VIDEO_URL = (
    "https://archive.org/download/"
    f"{ARCHIVE_IDENTIFIER}/{quote(ARCHIVE_FILENAME)}"
)
SOURCE_PAGE = f"https://archive.org/details/{ARCHIVE_IDENTIFIER}"
EXPECTED_SHA1 = "7ece11d9f9fc5c33eb793f7a85a8ad9bf1e009e5"
MAX_VIDEO_BYTES = 80 * 1024 * 1024


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Download an attributed public-domain roadside-cleanup video for "
            "functional stream testing. The video remains excluded from Git."
        )
    )
    parser.add_argument(
        "--output",
        default="media/demo-video/wsdot-adopt-a-highway-safety.mp4",
    )
    parser.add_argument("--timeout", type=float, default=60.0)
    parser.add_argument("--refresh", action="store_true")
    parser.add_argument(
        "--format",
        choices=("json", "path"),
        default="json",
        dest="output_format",
    )
    return parser


def _manifest(target: Path, sha256: str) -> dict[str, Any]:
    return {
        "title": "WSDOT Adopt-a-Highway Safety Video",
        "creator": "Washington State Department of Transportation",
        "purpose": (
            "Functional video-stream testing only; this is not a labelled "
            "accuracy dataset."
        ),
        "source_page": SOURCE_PAGE,
        "download_url": VIDEO_URL,
        "archive_identifier": ARCHIVE_IDENTIFIER,
        "license": {
            "name": "Public Domain Mark 1.0",
            "url": "https://creativecommons.org/publicdomain/mark/1.0/",
        },
        "local_file": target.name,
        "sha1": EXPECTED_SHA1,
        "sha256": sha256,
        "downloaded_at": datetime.now(timezone.utc).isoformat(),
    }


def _read_cached(target: Path, manifest_path: Path) -> dict[str, Any] | None:
    if not target.is_file() or not manifest_path.is_file():
        return None
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if manifest.get("sha1") != EXPECTED_SHA1:
        return None
    sha1 = hashlib.sha1(target.read_bytes()).hexdigest()
    if sha1 != EXPECTED_SHA1:
        return None
    return {
        "cached": True,
        "video": str(target),
        "manifest": str(manifest_path),
        "license": manifest["license"],
    }


def prepare_demo_video(
    output: str | Path,
    *,
    timeout: float = 60.0,
    refresh: bool = False,
    video_url: str = VIDEO_URL,
    expected_sha1: str = EXPECTED_SHA1,
) -> dict[str, Any]:
    if timeout <= 0:
        raise ValueError("timeout must be positive.")
    parsed = urlsplit(video_url)
    if parsed.scheme != "https" or not parsed.netloc:
        raise ValueError("The demo video URL must use HTTPS.")
    target = Path(output).expanduser().resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    manifest_path = target.parent / "manifest.json"
    if not refresh and expected_sha1 == EXPECTED_SHA1:
        cached = _read_cached(target, manifest_path)
        if cached is not None:
            return cached

    request = Request(
        video_url,
        headers={"User-Agent": f"edge-litter-detection/{__version__}"},
    )
    temporary_path: Path | None = None
    sha1 = hashlib.sha1()
    sha256 = hashlib.sha256()
    written = 0
    prefix = b""
    try:
        with urlopen(request, timeout=timeout) as response:
            final_url = urlsplit(response.geturl())
            if final_url.scheme != "https":
                raise ValueError("The demo video redirected away from HTTPS.")
            declared_size = response.headers.get("Content-Length")
            if declared_size and int(declared_size) > MAX_VIDEO_BYTES:
                raise ValueError(
                    f"Demo video exceeds {MAX_VIDEO_BYTES} bytes."
                )
            with tempfile.NamedTemporaryFile(
                dir=target.parent,
                prefix=f".{target.name}.",
                delete=False,
            ) as temporary:
                temporary_path = Path(temporary.name)
                while True:
                    chunk = response.read(1024 * 1024)
                    if not chunk:
                        break
                    written += len(chunk)
                    if written > MAX_VIDEO_BYTES:
                        raise ValueError(
                            f"Demo video exceeds {MAX_VIDEO_BYTES} bytes."
                        )
                    if len(prefix) < 16:
                        prefix += chunk[: 16 - len(prefix)]
                    sha1.update(chunk)
                    sha256.update(chunk)
                    temporary.write(chunk)
        if len(prefix) < 12 or b"ftyp" not in prefix[4:16]:
            raise ValueError("Downloaded demo content is not an MP4 file.")
        observed_sha1 = sha1.hexdigest()
        if observed_sha1.lower() != expected_sha1.lower():
            raise ValueError(
                "Demo video SHA-1 mismatch: "
                f"expected {expected_sha1}, observed {observed_sha1}."
            )
        assert temporary_path is not None
        os.replace(temporary_path, target)
        temporary_path = None
        manifest = _manifest(target, sha256.hexdigest())
        manifest["download_url"] = video_url
        manifest["sha1"] = expected_sha1.lower()
        manifest_path.write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)

    return {
        "cached": False,
        "video": str(target),
        "manifest": str(manifest_path),
        "license": manifest["license"],
    }


def main() -> None:
    args = build_parser().parse_args()
    result = prepare_demo_video(
        args.output,
        timeout=args.timeout,
        refresh=args.refresh,
    )
    if args.output_format == "path":
        print(result["video"])
    else:
        print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
