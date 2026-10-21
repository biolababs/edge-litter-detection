from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

from . import __version__
from .common import write_json


VIDEO_URL = (
    "https://upload.wikimedia.org/wikipedia/commons/d/d4/"
    "Recycling_Video.webm"
)
SOURCE_PAGE = "https://commons.wikimedia.org/wiki/File:Recycling_Video.webm"
UPSTREAM_SHA1 = "ad3b141fdf60830572e091dd3f8e9df1cc2df6ed"
EXPECTED_SHA256 = (
    "fce18e73dd52a5c27dac03971915b757"
    "82cd8c6a093f630980a41f16d002d5e1"
)
MAX_VIDEO_BYTES = 80 * 1024 * 1024


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Download an attributed recycling-facility conveyor video for "
            "functional stream testing. The video remains excluded from Git."
        )
    )
    parser.add_argument(
        "--output",
        default="media/demo-video/recycling-facility.webm",
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
        "title": "Recycling Video",
        "creator": "Ireland4me (Wikimedia Commons contributor)",
        "attribution": (
            '"Recycling Video" by Ireland4me, licensed under CC BY-SA 3.0, '
            "via Wikimedia Commons."
        ),
        "purpose": (
            "Functional recycling-line video-stream testing only; this is "
            "not a labelled accuracy dataset."
        ),
        "source_page": SOURCE_PAGE,
        "download_url": VIDEO_URL,
        "upstream_permission": "Wikimedia VRTS permission confirmed",
        "license": {
            "name": "Creative Commons Attribution-ShareAlike 3.0",
            "identifier": "CC-BY-SA-3.0",
            "url": "https://creativecommons.org/licenses/by-sa/3.0/",
        },
        "local_file": target.name,
        "upstream_sha1": UPSTREAM_SHA1,
        "sha256": sha256,
        "downloaded_at": datetime.now(timezone.utc).isoformat(),
    }


def _is_supported_video(prefix: bytes) -> bool:
    is_webm = prefix.startswith(b"\x1a\x45\xdf\xa3")
    is_mp4 = len(prefix) >= 12 and b"ftyp" in prefix[4:32]
    return is_webm or is_mp4


def _read_cached(target: Path, manifest_path: Path) -> dict[str, Any] | None:
    if not target.is_file() or not manifest_path.is_file():
        return None
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if manifest.get("sha256") != EXPECTED_SHA256:
        return None
    digest = hashlib.sha256()
    try:
        with target.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError:
        return None
    if digest.hexdigest() != EXPECTED_SHA256:
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
    expected_sha256: str = EXPECTED_SHA256,
) -> dict[str, Any]:
    if timeout <= 0:
        raise ValueError("timeout must be positive.")
    parsed = urlsplit(video_url)
    if parsed.scheme != "https" or not parsed.netloc:
        raise ValueError("The demo video URL must use HTTPS.")
    target = Path(output).expanduser().resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    manifest_path = target.parent / "manifest.json"
    if not refresh and expected_sha256 == EXPECTED_SHA256:
        cached = _read_cached(target, manifest_path)
        if cached is not None:
            return cached

    request = Request(
        video_url,
        headers={"User-Agent": f"edge-litter-detection/{__version__}"},
    )
    temporary_path: Path | None = None
    sha256 = hashlib.sha256()
    written = 0
    prefix = b""
    try:
        # HTTPS was validated above and is revalidated after redirects.
        with urlopen(request, timeout=timeout) as response:  # nosec B310
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
                    if len(prefix) < 32:
                        prefix += chunk[: 32 - len(prefix)]
                    sha256.update(chunk)
                    temporary.write(chunk)
        if not _is_supported_video(prefix):
            raise ValueError(
                "Downloaded demo content is not a supported WebM or MP4 file."
            )
        observed_sha256 = sha256.hexdigest()
        if observed_sha256.lower() != expected_sha256.lower():
            raise ValueError(
                "Demo video SHA-256 mismatch: "
                f"expected {expected_sha256}, observed {observed_sha256}."
            )
        if temporary_path is None:
            raise RuntimeError("The demo video download did not create a file.")
        os.replace(temporary_path, target)
        temporary_path = None
        manifest = _manifest(target, observed_sha256)
        manifest["download_url"] = video_url
        manifest["sha256"] = expected_sha256.lower()
        write_json(manifest_path, manifest)
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
