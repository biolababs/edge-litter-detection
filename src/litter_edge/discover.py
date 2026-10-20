from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .common import utc_now, write_json
from .runtime import _is_image_source, _safe_source_label, _source_value


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Discover local cameras or probe an image, video, or stream."
    )
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument(
        "--list-cameras",
        action="store_true",
        help="Probe local camera indexes from 0 through --max-index.",
    )
    source.add_argument(
        "--source",
        help="Image/video path, camera index, or stream URL to probe.",
    )
    parser.add_argument("--max-index", type=int, default=8)
    parser.add_argument("--output", help="Optional JSON report path.")
    return parser


def _source_kind(source: str | int) -> str:
    if isinstance(source, int):
        return "camera"
    if "://" in source:
        return "stream"
    if _is_image_source(source):
        return "image"
    return "video"


def _frame_dimensions(frame: Any) -> tuple[int | None, int | None]:
    shape = getattr(frame, "shape", None)
    if not shape or len(shape) < 2:
        return None, None
    return int(shape[1]), int(shape[0])


def probe_source(source: str | int, cv2_module: Any | None = None) -> dict[str, Any]:
    if cv2_module is None:
        try:
            import cv2 as cv2_module
        except ImportError as exc:
            raise RuntimeError(
                "OpenCV is required for source discovery. Install the "
                "'runtime' optional dependency."
            ) from exc

    source_value = _source_value(source) if isinstance(source, str) else source
    result: dict[str, Any] = {
        "source": _safe_source_label(source_value),
        "kind": _source_kind(source_value),
        "available": False,
        "frame_read": False,
        "width": None,
        "height": None,
        "reported_fps": None,
        "backend": None,
    }

    if _is_image_source(source_value):
        frame = cv2_module.imread(str(source_value))
        if frame is None:
            return result
        width, height = _frame_dimensions(frame)
        result.update(
            {
                "available": True,
                "frame_read": True,
                "width": width,
                "height": height,
            }
        )
        return result

    capture = cv2_module.VideoCapture(source_value)
    try:
        if not capture.isOpened():
            return result
        result["available"] = True
        try:
            result["backend"] = capture.getBackendName()
        except (AttributeError, RuntimeError):
            pass
        ok, frame = capture.read()
        result["frame_read"] = bool(ok)
        if ok:
            width, height = _frame_dimensions(frame)
            result["width"] = width
            result["height"] = height
        fps = float(capture.get(cv2_module.CAP_PROP_FPS) or 0.0)
        result["reported_fps"] = fps if fps > 0 else None
        return result
    finally:
        capture.release()


def discover_cameras(
    max_index: int,
    cv2_module: Any | None = None,
) -> list[dict[str, Any]]:
    if max_index < 0:
        raise ValueError("max_index cannot be negative.")
    return [
        result
        for index in range(max_index + 1)
        if (result := probe_source(index, cv2_module=cv2_module))["available"]
    ]


def main() -> None:
    args = build_parser().parse_args()
    if args.max_index < 0:
        raise ValueError("max_index cannot be negative.")
    if args.list_cameras:
        cameras = discover_cameras(args.max_index)
        payload: dict[str, Any] = {
            "created_at": utc_now(),
            "operation": "discover_cameras",
            "max_index": args.max_index,
            "camera_count": len(cameras),
            "cameras": cameras,
        }
        successful = any(camera["frame_read"] for camera in cameras)
    else:
        result = probe_source(str(args.source))
        payload = {
            "created_at": utc_now(),
            "operation": "probe_source",
            "result": result,
        }
        successful = bool(result["available"] and result["frame_read"])

    if args.output:
        write_json(Path(args.output), payload)
    print(json.dumps(payload, indent=2, sort_keys=True))
    if not successful:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
