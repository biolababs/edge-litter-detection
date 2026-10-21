from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit, urlunsplit
from urllib.request import Request, urlopen

from . import __version__


TACO_ANNOTATIONS_URL = (
    "https://raw.githubusercontent.com/pedropro/TACO/master/"
    "data/annotations.json"
)
PREFERRED_CATEGORY_TERMS = (
    "bottle",
    "can",
    "cup",
    "cigarette",
    "plastic bag",
    "paper",
    "cardboard",
    "battery",
)
MAX_ANNOTATIONS_BYTES = 20 * 1024 * 1024
MAX_IMAGE_BYTES = 25 * 1024 * 1024
DEFAULT_TACO_IMAGE_LICENSE = {
    "name": "CC BY 4.0",
    "url": "https://creativecommons.org/licenses/by/4.0/",
    "basis": "TACO default when an image license entry is missing",
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Download a small, attributed TACO litter-image set for functional "
            "testing. Images remain excluded from Git."
        )
    )
    parser.add_argument("--output", default="media/taco-demo")
    parser.add_argument("--limit", type=int, default=8)
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument("--refresh", action="store_true")
    parser.add_argument("--annotations-url", default=TACO_ANNOTATIONS_URL)
    parser.add_argument(
        "--format",
        choices=("json", "path"),
        default="json",
        dest="output_format",
        help="Print the complete JSON result or only the first image path.",
    )
    return parser


def _https_url(value: object, *, allow_upgrade: bool = False) -> str:
    raw = str(value or "").strip()
    parsed = urlsplit(raw)
    if parsed.scheme == "http" and allow_upgrade:
        parsed = parsed._replace(scheme="https")
        raw = urlunsplit(parsed)
    if parsed.scheme not in {"https"} or not parsed.netloc:
        raise ValueError(f"Only HTTPS download URLs are allowed: {raw!r}")
    return raw


def _read_url(url: str, timeout: float, maximum_bytes: int) -> bytes:
    request = Request(
        _https_url(url, allow_upgrade=True),
        headers={"User-Agent": f"edge-litter-detection/{__version__}"},
    )
    # HTTPS is validated before the request and again after redirects.
    with urlopen(request, timeout=timeout) as response:  # nosec B310
        final_url = response.geturl()
        _https_url(final_url)
        declared_size = response.headers.get("Content-Length")
        if declared_size and int(declared_size) > maximum_bytes:
            raise ValueError(f"Download exceeds {maximum_bytes} bytes: {final_url}")
        content = response.read(maximum_bytes + 1)
    if len(content) > maximum_bytes:
        raise ValueError(f"Download exceeds {maximum_bytes} bytes: {url}")
    return content


def _looks_like_image(content: bytes) -> bool:
    return (
        content.startswith(b"\xff\xd8\xff")
        or content.startswith(b"\x89PNG\r\n\x1a\n")
        or (
            len(content) >= 12
            and content.startswith(b"RIFF")
            and content[8:12] == b"WEBP"
        )
    )


def _image_extension(image: dict[str, Any], content: bytes) -> str:
    suffix = Path(str(image.get("file_name") or "")).suffix.lower()
    if suffix in {".jpeg", ".jpg", ".png", ".webp"}:
        return ".jpg" if suffix == ".jpeg" else suffix
    if content.startswith(b"\x89PNG"):
        return ".png"
    if content.startswith(b"RIFF"):
        return ".webp"
    return ".jpg"


def _candidate_url(image: dict[str, Any]) -> str | None:
    for key in ("flickr_640_url", "coco_url", "flickr_url"):
        value = str(image.get(key) or "").strip()
        if value:
            try:
                return _https_url(value, allow_upgrade=True)
            except ValueError:
                continue
    return None


def _license_metadata(
    image: dict[str, Any],
    license_by_id: dict[int, dict[str, Any]],
) -> dict[str, Any]:
    value = image.get("license")
    if value in (None, "", [], {}):
        return dict(DEFAULT_TACO_IMAGE_LICENSE)
    try:
        license_id = int(value)
    except (TypeError, ValueError):
        return {
            "name": "Unresolved TACO image license",
            "raw_value": value,
        }
    license_record = license_by_id.get(license_id)
    if license_record is None:
        return {
            "id": license_id,
            "name": "Unresolved TACO image license ID",
        }
    return dict(license_record)


def _ranked_images(payload: dict[str, Any]) -> list[dict[str, Any]]:
    categories = {
        int(category["id"]): str(category["name"])
        for category in payload.get("categories", [])
        if "id" in category and "name" in category
    }
    image_categories: dict[int, set[str]] = {}
    annotation_counts: dict[int, int] = {}
    for annotation in payload.get("annotations", []):
        try:
            image_id = int(annotation["image_id"])
            category_name = categories[int(annotation["category_id"])]
        except (KeyError, TypeError, ValueError):
            continue
        image_categories.setdefault(image_id, set()).add(category_name)
        annotation_counts[image_id] = annotation_counts.get(image_id, 0) + 1

    ranked: list[tuple[int, int, int, dict[str, Any]]] = []
    for image in payload.get("images", []):
        try:
            image_id = int(image["id"])
        except (KeyError, TypeError, ValueError):
            continue
        if _candidate_url(image) is None:
            continue
        names = image_categories.get(image_id, set())
        preferred = sum(
            1
            for name in names
            if any(term in name.lower() for term in PREFERRED_CATEGORY_TERMS)
        )
        ranked.append(
            (
                -preferred,
                -annotation_counts.get(image_id, 0),
                image_id,
                image,
            )
        )
    ranked.sort(key=lambda item: item[:3])
    return [item[3] for item in ranked]


def _cached_result(output: Path, limit: int) -> dict[str, Any] | None:
    manifest_path = output / "manifest.json"
    if not manifest_path.is_file():
        return None
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        images = manifest["images"]
        existing = [
            output / str(item["local_file"])
            for item in images
            if (output / str(item["local_file"])).is_file()
        ]
    except (KeyError, OSError, TypeError, ValueError, json.JSONDecodeError):
        return None
    if len(existing) < limit:
        return None
    return {
        "dataset": "TACO",
        "cached": True,
        "count": len(existing),
        "first_image": str(existing[0]),
        "manifest": str(manifest_path),
    }


def prepare_demo_data(
    output: str | Path,
    limit: int = 8,
    timeout: float = 30.0,
    annotations_url: str = TACO_ANNOTATIONS_URL,
    refresh: bool = False,
) -> dict[str, Any]:
    if limit <= 0:
        raise ValueError("limit must be positive.")
    if limit > 100:
        raise ValueError("limit must not exceed 100 images.")
    if timeout <= 0:
        raise ValueError("timeout must be positive.")
    destination = Path(output).expanduser().resolve()
    destination.mkdir(parents=True, exist_ok=True)

    if not refresh:
        cached = _cached_result(destination, limit)
        if cached is not None:
            return cached

    annotations_bytes = _read_url(
        annotations_url,
        timeout=timeout,
        maximum_bytes=MAX_ANNOTATIONS_BYTES,
    )
    payload = json.loads(annotations_bytes.decode("utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("TACO annotations must be a JSON object.")
    license_by_id = {
        int(license_record["id"]): license_record
        for license_record in payload.get("licenses", [])
        if "id" in license_record
    }
    categories = {
        int(category["id"]): str(category["name"])
        for category in payload.get("categories", [])
        if "id" in category and "name" in category
    }
    categories_by_image: dict[int, set[str]] = {}
    for annotation in payload.get("annotations", []):
        try:
            image_id = int(annotation["image_id"])
            name = categories[int(annotation["category_id"])]
        except (KeyError, TypeError, ValueError):
            continue
        categories_by_image.setdefault(image_id, set()).add(name)

    downloaded: list[dict[str, Any]] = []
    failures: list[dict[str, str]] = []
    ranked_images = _ranked_images(payload)
    maximum_attempts = min(len(ranked_images), max(limit * 2, limit + 8))
    attempts = 0
    for image in ranked_images[:maximum_attempts]:
        if len(downloaded) >= limit:
            break
        attempts += 1
        image_id = int(image["id"])
        source_url = _candidate_url(image)
        if source_url is None:
            continue
        temporary_path: Path | None = None
        try:
            content = _read_url(
                source_url,
                timeout=timeout,
                maximum_bytes=MAX_IMAGE_BYTES,
            )
            if not _looks_like_image(content):
                raise ValueError("Downloaded content is not JPEG, PNG, or WebP.")
            suffix = _image_extension(image, content)
            filename = f"taco-{image_id:06d}{suffix}"
            target = destination / filename
            with tempfile.NamedTemporaryFile(
                dir=destination,
                prefix=f".{filename}.",
                delete=False,
            ) as temporary:
                temporary.write(content)
                temporary_path = Path(temporary.name)
            os.replace(temporary_path, target)
        except Exception as exc:
            failures.append({"image_id": str(image_id), "error": str(exc)})
            continue
        finally:
            if temporary_path is not None and temporary_path.exists():
                temporary_path.unlink()

        downloaded.append(
            {
                "image_id": image_id,
                "local_file": filename,
                "sha256": hashlib.sha256(content).hexdigest(),
                "categories": sorted(categories_by_image.get(image_id, set())),
                "source_url": source_url,
                "original_file_name": image.get("file_name"),
                "license": _license_metadata(image, license_by_id),
            }
        )

    if not downloaded:
        detail = failures[0]["error"] if failures else "No downloadable images found."
        raise RuntimeError(f"Unable to prepare TACO demo data: {detail}")

    manifest = {
        "schema_version": "1.0",
        "dataset": "TACO: Trash Annotations in Context",
        "dataset_repository": "https://github.com/pedropro/TACO",
        "annotations_url": annotations_url,
        "annotations_sha256": hashlib.sha256(annotations_bytes).hexdigest(),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "requested_image_count": limit,
        "download_attempt_count": attempts,
        "notice": (
            "TACO annotations are CC BY 4.0. Individual images can have "
            "different public licenses; retain and review each image's license "
            "metadata before redistribution."
        ),
        "images": downloaded,
        "failures": failures,
    }
    manifest_path = destination / "manifest.json"
    manifest_content = json.dumps(manifest, indent=2, sort_keys=True) + "\n"
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=destination,
        prefix=".manifest.",
        delete=False,
    ) as temporary_manifest:
        temporary_manifest.write(manifest_content)
        temporary_manifest_path = Path(temporary_manifest.name)
    try:
        os.replace(temporary_manifest_path, manifest_path)
    finally:
        if temporary_manifest_path.exists():
            temporary_manifest_path.unlink()
    result = {
        "dataset": "TACO",
        "cached": False,
        "count": len(downloaded),
        "first_image": str(destination / downloaded[0]["local_file"]),
        "manifest": str(manifest_path),
    }
    return result


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    try:
        result = prepare_demo_data(
            output=args.output,
            limit=args.limit,
            timeout=args.timeout,
            annotations_url=args.annotations_url,
            refresh=args.refresh,
        )
    except Exception as exc:
        print(f"ERROR: unable to prepare demo data: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
    if args.output_format == "path":
        print(result["first_image"])
    else:
        print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
