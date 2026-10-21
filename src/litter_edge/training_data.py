from __future__ import annotations

import argparse
import hashlib
from io import BytesIO
import json
import os
import random
import sys
import tempfile
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Callable
from urllib.parse import quote

import yaml

from .classes import load_class_names
from .demo_data import (
    MAX_ANNOTATIONS_BYTES,
    MAX_IMAGE_BYTES,
    TACO_ANNOTATIONS_URL,
    _candidate_url,
    _https_url,
    _image_extension,
    _license_metadata,
    _looks_like_image,
    _read_url,
)


TACO_REPOSITORY = "https://github.com/pedropro/TACO"
TACO_RAW_DATA_ROOT = (
    "https://raw.githubusercontent.com/pedropro/TACO/master/data"
)
SPLIT_NAMES = ("train", "valid", "test")

# TACO has a fine-grained packaging taxonomy. This mapping deliberately avoids
# claiming a material or object type that cannot be inferred from the source
# label. Remaining categories are retained as other_litter instead of dropped.
TACO_TO_OPERATIONAL = {
    "Clear plastic bottle": "plastic_bottle",
    "Other plastic bottle": "plastic_bottle",
    "Glass bottle": "glass_bottle",
    "Food Can": "metal_can",
    "Aerosol": "metal_can",
    "Drink can": "metal_can",
    "Magazine paper": "paper",
    "Tissues": "paper",
    "Wrapping paper": "paper",
    "Normal paper": "paper",
    "Paper bag": "paper",
    "Toilet tube": "cardboard",
    "Other carton": "cardboard",
    "Egg carton": "cardboard",
    "Drink carton": "cardboard",
    "Corrugated carton": "cardboard",
    "Meal carton": "cardboard",
    "Pizza box": "cardboard",
    "Garbage bag": "plastic_bag",
    "Single-use carrier bag": "plastic_bag",
    "Polypropylene bag": "plastic_bag",
    "Plastified paper bag": "plastic_bag",
    "Other plastic wrapper": "food_wrapper",
    "Crisp packet": "food_wrapper",
    "Paper cup": "disposable_cup",
    "Disposable plastic cup": "disposable_cup",
    "Foam cup": "disposable_cup",
    "Cigarette": "cigarette_butt",
    "Food waste": "food_waste",
    "Battery": "battery",
    "Broken glass": "broken_glass",
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Build an attributed, grouped COCO dataset from public TACO "
            "annotations for the project-maintained litter model."
        )
    )
    parser.add_argument("--output", default="data/taco-operational-v1")
    parser.add_argument("--class-names", default="config/classes.yaml")
    parser.add_argument("--annotations-url", default=TACO_ANNOTATIONS_URL)
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--train-ratio", type=float, default=0.70)
    parser.add_argument("--valid-ratio", type=float, default=0.15)
    parser.add_argument("--test-ratio", type=float, default=0.15)
    parser.add_argument(
        "--max-images",
        type=int,
        default=0,
        help="Optional bounded smoke-test subset; zero downloads all images.",
    )
    parser.add_argument("--refresh", action="store_true")
    return parser


def _atomic_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as temporary:
            json.dump(payload, temporary, indent=2, sort_keys=True)
            temporary.write("\n")
            temporary_path = Path(temporary.name)
        os.replace(temporary_path, path)
        temporary_path = None
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


def _atomic_yaml(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as temporary:
            yaml.safe_dump(payload, temporary, sort_keys=False)
            temporary_path = Path(temporary.name)
        os.replace(temporary_path, path)
        temporary_path = None
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


def _group_name(image: dict[str, Any]) -> str:
    raw_name = str(image.get("file_name") or "").replace("\\", "/")
    parts = [part for part in PurePosixPath(raw_name).parts if part not in {"", "."}]
    if len(parts) > 1 and parts[0] != "..":
        return parts[0]
    image_id = int(image["id"])
    return f"image-{image_id:08d}"


def _split_groups(
    group_names: set[str],
    *,
    seed: int,
    train_ratio: float,
    valid_ratio: float,
    test_ratio: float,
) -> dict[str, str]:
    ratios = (train_ratio, valid_ratio, test_ratio)
    if any(value <= 0 for value in ratios):
        raise ValueError("All split ratios must be positive.")
    if abs(sum(ratios) - 1.0) > 1e-6:
        raise ValueError("Train, validation, and test ratios must sum to 1.0.")
    if len(group_names) < 3:
        raise ValueError(
            "At least three independent TACO groups are required for grouped "
            "train, validation, and test splits."
        )

    ordered = sorted(group_names)
    random.Random(seed).shuffle(ordered)
    group_count = len(ordered)
    valid_count = max(1, round(group_count * valid_ratio))
    test_count = max(1, round(group_count * test_ratio))
    while valid_count + test_count >= group_count:
        if valid_count >= test_count and valid_count > 1:
            valid_count -= 1
        elif test_count > 1:
            test_count -= 1
        else:
            raise ValueError("Unable to preserve at least one training group.")
    train_count = group_count - valid_count - test_count

    assignments: dict[str, str] = {}
    for name in ordered[:train_count]:
        assignments[name] = "train"
    for name in ordered[train_count : train_count + valid_count]:
        assignments[name] = "valid"
    for name in ordered[train_count + valid_count :]:
        assignments[name] = "test"
    return assignments


def _limit_images_by_group(
    images: list[dict[str, Any]],
    maximum: int,
) -> list[dict[str, Any]]:
    if not maximum or maximum >= len(images):
        return images
    if maximum < 3:
        raise ValueError("max_images must be zero or at least 3.")
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for image in images:
        grouped[_group_name(image)].append(image)
    selected: list[dict[str, Any]] = []
    group_names = sorted(grouped)
    index = 0
    while len(selected) < maximum:
        added = False
        for group_name in group_names:
            bucket = grouped[group_name]
            if index < len(bucket):
                selected.append(bucket[index])
                added = True
                if len(selected) == maximum:
                    break
        if not added:
            break
        index += 1
    return sorted(selected, key=lambda image: int(image["id"]))


def _source_urls(image: dict[str, Any]) -> list[str]:
    candidates: list[str] = []
    primary = _candidate_url(image)
    if primary is not None:
        candidates.append(primary)
    for key in ("coco_url", "flickr_url"):
        raw = str(image.get(key) or "").strip()
        if not raw:
            continue
        try:
            candidates.append(_https_url(raw, allow_upgrade=True))
        except ValueError:
            continue

    file_name = str(image.get("file_name") or "").replace("\\", "/")
    path = PurePosixPath(file_name)
    if (
        file_name
        and not path.is_absolute()
        and ".." not in path.parts
    ):
        candidates.append(f"{TACO_RAW_DATA_ROOT}/{quote(file_name, safe='/')}")

    output: list[str] = []
    for candidate in candidates:
        if candidate not in output:
            output.append(candidate)
    return output


def _download_one(
    *,
    image: dict[str, Any],
    split: str,
    destination: Path,
    timeout: float,
    reader: Callable[[str, float, int], bytes],
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    image_id = int(image["id"])
    errors: list[str] = []
    for source_url in _source_urls(image):
        temporary_path: Path | None = None
        try:
            content = reader(source_url, timeout, MAX_IMAGE_BYTES)
            if not _looks_like_image(content):
                raise ValueError("content is not JPEG, PNG, or WebP")
            actual_width, actual_height = _image_dimensions(
                content,
                fallback_width=image.get("width"),
                fallback_height=image.get("height"),
            )
            extension = _image_extension(image, content)
            filename = f"taco-{image_id:06d}{extension}"
            target = destination / split / filename
            target.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(
                mode="wb",
                dir=target.parent,
                prefix=f".{filename}.",
                suffix=".download",
                delete=False,
            ) as temporary:
                temporary.write(content)
                temporary_path = Path(temporary.name)
            os.replace(temporary_path, target)
            temporary_path = None
            return (
                {
                    "image_id": image_id,
                    "split": split,
                    "local_file": f"{split}/{filename}",
                    "source_url": source_url,
                    "sha256": hashlib.sha256(content).hexdigest(),
                    "bytes": len(content),
                    "width": actual_width,
                    "height": actual_height,
                },
                None,
            )
        except Exception as exc:
            errors.append(f"{source_url}: {exc}")
        finally:
            if temporary_path is not None:
                temporary_path.unlink(missing_ok=True)
    return (
        None,
        {
            "image_id": image_id,
            "file_name": image.get("file_name"),
            "errors": errors or ["no HTTPS image source was available"],
        },
    )


def _image_dimensions(
    content: bytes,
    *,
    fallback_width: object,
    fallback_height: object,
) -> tuple[int, int]:
    try:
        from PIL import Image

        with Image.open(BytesIO(content)) as image:
            width, height = image.size
        if width > 0 and height > 0:
            return int(width), int(height)
    except (ImportError, OSError, ValueError):
        pass
    try:
        width = int(fallback_width)
        height = int(fallback_height)
    except (TypeError, ValueError) as exc:
        raise ValueError("Downloaded image dimensions could not be determined.") from exc
    if width <= 0 or height <= 0:
        raise ValueError("Downloaded image dimensions must be positive.")
    return width, height


def _scaled_segmentation(
    segmentation: object,
    scale_x: float,
    scale_y: float,
) -> object | None:
    if not isinstance(segmentation, list):
        return None
    scaled: list[list[float]] = []
    for polygon in segmentation:
        if not isinstance(polygon, list) or len(polygon) % 2:
            return None
        values: list[float] = []
        for index, coordinate in enumerate(polygon):
            factor = scale_x if index % 2 == 0 else scale_y
            values.append(float(coordinate) * factor)
        scaled.append(values)
    return scaled


def _cached_result(destination: Path) -> dict[str, Any] | None:
    manifest_path = destination / "manifest.json"
    if not manifest_path.is_file():
        return None
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        split_summaries = manifest["splits"]
        for split in SPLIT_NAMES:
            annotation_path = destination / split / "_annotations.coco.json"
            if not annotation_path.is_file():
                return None
            payload = json.loads(annotation_path.read_text(encoding="utf-8"))
            for image in payload.get("images", []):
                if not (destination / split / str(image["file_name"])).is_file():
                    return None
    except (KeyError, OSError, TypeError, ValueError, json.JSONDecodeError):
        return None
    return {
        "dataset": "TACO operational mapping",
        "cached": True,
        "output": str(destination),
        "manifest": str(manifest_path),
        "splits": split_summaries,
        "classes_without_instances": manifest.get("classes_without_instances", []),
    }


def _validate_source_payload(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError("TACO annotations must be a JSON object.")
    for key in ("images", "annotations", "categories"):
        if not isinstance(payload.get(key), list):
            raise ValueError(f"TACO annotations must contain a {key!r} list.")
    return payload


def prepare_training_data(
    *,
    output: str | Path,
    class_names_file: str | Path = "config/classes.yaml",
    annotations_url: str = TACO_ANNOTATIONS_URL,
    timeout: float = 30.0,
    workers: int = 8,
    seed: int = 42,
    train_ratio: float = 0.70,
    valid_ratio: float = 0.15,
    test_ratio: float = 0.15,
    max_images: int = 0,
    refresh: bool = False,
    reader: Callable[[str, float, int], bytes] = _read_url,
) -> dict[str, Any]:
    if timeout <= 0:
        raise ValueError("timeout must be positive.")
    if workers <= 0 or workers > 64:
        raise ValueError("workers must be between 1 and 64.")
    if max_images < 0:
        raise ValueError("max_images cannot be negative.")

    destination = Path(output).expanduser().resolve()
    destination.mkdir(parents=True, exist_ok=True)
    if not refresh:
        cached = _cached_result(destination)
        if cached is not None:
            return cached

    class_names = load_class_names(class_names_file)
    class_id_by_name = {name: class_id for class_id, name in class_names.items()}
    required_names = set(TACO_TO_OPERATIONAL.values()) | {"other_litter"}
    missing_names = sorted(required_names - set(class_id_by_name))
    if missing_names:
        raise ValueError(
            "Configured taxonomy is missing mapped classes: "
            + ", ".join(missing_names)
        )

    annotations_bytes = reader(
        annotations_url,
        timeout,
        MAX_ANNOTATIONS_BYTES,
    )
    source = _validate_source_payload(
        json.loads(annotations_bytes.decode("utf-8"))
    )
    source_categories = {
        int(category["id"]): str(category["name"])
        for category in source["categories"]
        if "id" in category and "name" in category
    }
    license_by_id = {
        int(record["id"]): record
        for record in source.get("licenses", [])
        if isinstance(record, dict) and "id" in record
    }

    images = [
        image
        for image in source["images"]
        if isinstance(image, dict)
        and "id" in image
        and _source_urls(image)
    ]
    images.sort(key=lambda image: int(image["id"]))
    images = _limit_images_by_group(images, max_images)
    if not images:
        raise RuntimeError("No downloadable TACO images were found.")

    groups = {_group_name(image) for image in images}
    assignments = _split_groups(
        groups,
        seed=seed,
        train_ratio=train_ratio,
        valid_ratio=valid_ratio,
        test_ratio=test_ratio,
    )
    image_split = {
        int(image["id"]): assignments[_group_name(image)]
        for image in images
    }

    downloaded: dict[int, dict[str, Any]] = {}
    failures: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {
            executor.submit(
                _download_one,
                image=image,
                split=image_split[int(image["id"])],
                destination=destination,
                timeout=timeout,
                reader=reader,
            ): image
            for image in images
        }
        for future in as_completed(futures):
            record, failure = future.result()
            if record is not None:
                downloaded[int(record["image_id"])] = record
            if failure is not None:
                failures.append(failure)
    if not downloaded:
        detail = failures[0]["errors"][0] if failures else "unknown download failure"
        raise RuntimeError(f"No TACO images could be downloaded: {detail}")

    source_images_by_id = {
        int(image["id"]): image
        for image in images
        if int(image["id"]) in downloaded
    }
    annotations_by_split: dict[str, list[dict[str, Any]]] = defaultdict(list)
    mapped_counts: Counter[str] = Counter()
    source_mapping_counts: Counter[tuple[str, str]] = Counter()
    invalid_annotations: list[dict[str, Any]] = []
    other_name = "other_litter"
    for source_index, annotation in enumerate(source["annotations"], start=1):
        if not isinstance(annotation, dict):
            continue
        try:
            image_id = int(annotation["image_id"])
            source_name = source_categories[int(annotation["category_id"])]
            bbox = [float(value) for value in annotation["bbox"]]
        except (KeyError, TypeError, ValueError):
            continue
        if image_id not in downloaded:
            continue
        if len(bbox) != 4 or bbox[2] <= 0 or bbox[3] <= 0:
            invalid_annotations.append(
                {"annotation_id": annotation.get("id"), "reason": "invalid_bbox"}
            )
            continue
        operational_name = TACO_TO_OPERATIONAL.get(source_name, other_name)
        operational_id = class_id_by_name[operational_name]
        source_image = source_images_by_id[image_id]
        try:
            source_width = int(source_image["width"])
            source_height = int(source_image["height"])
            actual_width = int(downloaded[image_id]["width"])
            actual_height = int(downloaded[image_id]["height"])
        except (KeyError, TypeError, ValueError):
            invalid_annotations.append(
                {
                    "annotation_id": annotation.get("id"),
                    "reason": "missing_image_dimensions",
                }
            )
            continue
        if min(source_width, source_height, actual_width, actual_height) <= 0:
            invalid_annotations.append(
                {
                    "annotation_id": annotation.get("id"),
                    "reason": "invalid_image_dimensions",
                }
            )
            continue
        scale_x = actual_width / source_width
        scale_y = actual_height / source_height
        bbox = [
            bbox[0] * scale_x,
            bbox[1] * scale_y,
            bbox[2] * scale_x,
            bbox[3] * scale_y,
        ]
        try:
            annotation_id = int(annotation.get("id", source_index))
        except (TypeError, ValueError):
            annotation_id = source_index
        source_area = annotation.get("area")
        area = (
            float(source_area) * scale_x * scale_y
            if source_area is not None
            else bbox[2] * bbox[3]
        )
        normalized = {
            "id": annotation_id,
            "image_id": image_id,
            "category_id": operational_id,
            "bbox": bbox,
            "area": area,
            "iscrowd": int(annotation.get("iscrowd", 0)),
        }
        scaled_segmentation = _scaled_segmentation(
            annotation.get("segmentation"),
            scale_x,
            scale_y,
        )
        if scaled_segmentation is not None:
            normalized["segmentation"] = scaled_segmentation
        split = downloaded[image_id]["split"]
        annotations_by_split[split].append(normalized)
        mapped_counts[operational_name] += 1
        source_mapping_counts[(source_name, operational_name)] += 1

    categories = [
        {"id": class_id, "name": class_name, "supercategory": "litter"}
        for class_id, class_name in class_names.items()
    ]
    split_summaries: dict[str, dict[str, Any]] = {}
    for split in SPLIT_NAMES:
        split_images: list[dict[str, Any]] = []
        split_downloads = sorted(
            (
                record
                for record in downloaded.values()
                if record["split"] == split
            ),
            key=lambda record: int(record["image_id"]),
        )
        for record in split_downloads:
            source_image = source_images_by_id[int(record["image_id"])]
            split_images.append(
                {
                    "id": int(record["image_id"]),
                    "file_name": Path(record["local_file"]).name,
                    "width": int(record["width"]),
                    "height": int(record["height"]),
                    "license": source_image.get("license"),
                    "date_captured": source_image.get("date_captured"),
                }
            )
        split_annotations = sorted(
            annotations_by_split.get(split, []),
            key=lambda annotation: int(annotation["id"]),
        )
        coco_payload = {
            "info": {
                "description": (
                    "TACO mapped to the Edge Litter Detection operational taxonomy"
                ),
                "version": "1.0",
                "date_created": datetime.now(timezone.utc).isoformat(),
                "source": TACO_REPOSITORY,
            },
            "licenses": source.get("licenses", []),
            "images": split_images,
            "annotations": split_annotations,
            "categories": categories,
        }
        _atomic_json(
            destination / split / "_annotations.coco.json",
            coco_payload,
        )
        split_groups = sorted(
            {
                _group_name(source_images_by_id[int(record["image_id"])])
                for record in split_downloads
            }
        )
        split_summaries[split] = {
            "images": len(split_images),
            "annotations": len(split_annotations),
            "groups": split_groups,
        }

    classes_without_instances = [
        name for name in class_names.values() if mapped_counts[name] == 0
    ]
    mapping_records = [
        {
            "source_category": source_name,
            "operational_category": operational_name,
            "annotations": count,
        }
        for (source_name, operational_name), count in sorted(
            source_mapping_counts.items()
        )
    ]
    downloads = [
        {
            **record,
            "original_file_name": source_images_by_id[image_id].get("file_name"),
            "annotation_width": source_images_by_id[image_id].get("width"),
            "annotation_height": source_images_by_id[image_id].get("height"),
            "license": _license_metadata(
                source_images_by_id[image_id],
                license_by_id,
            ),
        }
        for image_id, record in sorted(downloaded.items())
    ]
    manifest = {
        "schema_version": "1.1",
        "dataset": "TACO operational mapping",
        "dataset_repository": TACO_REPOSITORY,
        "annotations_url": annotations_url,
        "annotations_sha256": hashlib.sha256(annotations_bytes).hexdigest(),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "format": "COCO",
        "seed": seed,
        "split_policy": "grouped_by_taco_batch_or_original_source_group",
        "split_ratios": {
            "train": train_ratio,
            "valid": valid_ratio,
            "test": test_ratio,
        },
        "splits": split_summaries,
        "classes": [
            {"id": class_id, "name": class_name}
            for class_id, class_name in class_names.items()
        ],
        "class_instance_counts": {
            name: mapped_counts[name] for name in class_names.values()
        },
        "classes_without_instances": classes_without_instances,
        "source_category_mapping": mapping_records,
        "downloaded_images": downloads,
        "download_failures": sorted(
            failures,
            key=lambda failure: int(failure["image_id"]),
        ),
        "invalid_annotations": invalid_annotations,
        "training_data_status": "bootstrap_only",
        "release_blockers": [
            "add representative truck, roadside, camera, weather, and motion data",
            "supply labeled examples for every released class",
            "freeze and checksum the held-out test set",
            "complete detection, counting, and target-device acceptance tests",
        ],
        "notice": (
            "TACO annotations are CC BY 4.0. Individual images can have "
            "different public licenses. Preserve the per-image metadata in "
            "this manifest and review redistribution terms before publishing "
            "a derived dataset or model. Bounding boxes and polygon coordinates "
            "are scaled from the annotation dimensions to the dimensions of "
            "the downloaded public image artifact."
        ),
    }
    _atomic_json(destination / "manifest.json", manifest)
    _atomic_yaml(
        destination / "classes.yaml",
        {
            "schema_version": "2.0",
            "names": class_names,
        },
    )
    return {
        "dataset": "TACO operational mapping",
        "cached": False,
        "output": str(destination),
        "manifest": str(destination / "manifest.json"),
        "splits": split_summaries,
        "classes_without_instances": classes_without_instances,
    }


def main() -> None:
    args = build_parser().parse_args()
    try:
        result = prepare_training_data(
            output=args.output,
            class_names_file=args.class_names,
            annotations_url=args.annotations_url,
            timeout=args.timeout,
            workers=args.workers,
            seed=args.seed,
            train_ratio=args.train_ratio,
            valid_ratio=args.valid_ratio,
            test_ratio=args.test_ratio,
            max_images=args.max_images,
            refresh=args.refresh,
        )
    except Exception as exc:
        print(f"ERROR: unable to prepare training data: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
    print(json.dumps(result, indent=2, sort_keys=True))
    if result["classes_without_instances"]:
        print(
            "WARNING: no TACO training instances for: "
            + ", ".join(result["classes_without_instances"]),
            file=sys.stderr,
        )


if __name__ == "__main__":
    main()
