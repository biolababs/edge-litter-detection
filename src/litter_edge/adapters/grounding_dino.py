from __future__ import annotations

from contextlib import nullcontext
from typing import Any

from ..schema import Detection


def _normalize_label(value: object) -> str:
    return " ".join(str(value).lower().replace("_", " ").strip(" .").split())


def _to_list(value: Any) -> list[Any]:
    if hasattr(value, "tolist"):
        return list(value.tolist())
    return list(value)


def _box_iou(left: Detection, right: Detection) -> float:
    x1 = max(left.x1, right.x1)
    y1 = max(left.y1, right.y1)
    x2 = min(left.x2, right.x2)
    y2 = min(left.y2, right.y2)
    intersection = max(0.0, x2 - x1) * max(0.0, y2 - y1)
    if intersection == 0.0:
        return 0.0
    left_area = max(0.0, left.x2 - left.x1) * max(0.0, left.y2 - left.y1)
    right_area = max(0.0, right.x2 - right.x1) * max(0.0, right.y2 - right.y1)
    union = left_area + right_area - intersection
    return intersection / union if union > 0.0 else 0.0


def _class_agnostic_nms(
    detections: list[Detection],
    iou_threshold: float,
    maximum: int,
) -> list[Detection]:
    selected: list[Detection] = []
    for detection in sorted(
        detections,
        key=lambda item: item.confidence,
        reverse=True,
    ):
        if all(_box_iou(detection, existing) <= iou_threshold for existing in selected):
            selected.append(detection)
            if len(selected) >= maximum:
                break
    return selected


class GroundingDINODetector:
    """Public open-vocabulary detector loaded from Hugging Face."""

    backend_name = "grounding_dino"

    def __init__(
        self,
        model_reference: str,
        class_names: dict[int, str],
        confidence: float,
        device: str,
        optimize: bool = True,
        class_prompts: dict[int, str] | None = None,
        nms_iou: float = 0.6,
        max_detections: int = 100,
    ) -> None:
        try:
            import torch
            from transformers import (
                AutoModelForZeroShotObjectDetection,
                AutoProcessor,
            )
        except ImportError as exc:
            raise RuntimeError(
                "The public Grounding DINO runtime is not installed. Install "
                "the 'public-model' optional dependency."
            ) from exc

        self.torch = torch
        self.device = device
        self.class_names = class_names
        self.class_prompts = class_prompts or {
            class_id: name.replace("_", " ")
            for class_id, name in class_names.items()
        }
        if set(self.class_prompts) != set(self.class_names):
            raise ValueError("Grounding DINO prompts must match all class IDs.")
        self.prompt_to_class_id = {
            _normalize_label(prompt): class_id
            for class_id, prompt in self.class_prompts.items()
        }
        self.prompt_list = [
            self.class_prompts[class_id] for class_id in sorted(self.class_names)
        ]
        self.confidence = confidence
        self.nms_iou = nms_iou
        self.max_detections = max_detections
        self.use_autocast = optimize and device.startswith("cuda")

        self.processor = AutoProcessor.from_pretrained(model_reference)
        self.model = AutoModelForZeroShotObjectDetection.from_pretrained(
            model_reference
        )
        self.model.to(device)
        self.model.eval()

    def _class_id_for_label(self, label: object) -> int:
        if isinstance(label, int):
            if label in self.class_names:
                return label
            raise RuntimeError(f"Grounding DINO returned unknown class ID: {label}")
        normalized = _normalize_label(label)
        exact = self.prompt_to_class_id.get(normalized)
        if exact is not None:
            return exact
        candidates = [
            class_id
            for prompt, class_id in self.prompt_to_class_id.items()
            if normalized in prompt or prompt in normalized
        ]
        if len(candidates) == 1:
            return candidates[0]
        raise RuntimeError(
            f"Grounding DINO returned an unmapped text label: {label!r}"
        )

    def predict(self, frame_bgr: Any) -> list[Detection]:
        frame_rgb = frame_bgr[:, :, ::-1].copy()
        try:
            inputs = self.processor(
                images=frame_rgb,
                text=[self.prompt_list],
                return_tensors="pt",
            )
        except (TypeError, ValueError):
            inputs = self.processor(
                images=frame_rgb,
                text=". ".join(self.prompt_list) + ".",
                return_tensors="pt",
            )
        if hasattr(inputs, "to"):
            inputs = inputs.to(self.device)

        autocast_context = nullcontext()
        if self.use_autocast and hasattr(self.torch, "autocast"):
            autocast_context = self.torch.autocast(
                device_type="cuda",
                dtype=self.torch.float16,
            )
        with self.torch.inference_mode(), autocast_context:
            outputs = self.model(**inputs)

        target_sizes = [tuple(int(value) for value in frame_rgb.shape[:2])]
        postprocess = self.processor.post_process_grounded_object_detection
        try:
            results = postprocess(
                outputs,
                inputs.get("input_ids"),
                threshold=self.confidence,
                text_threshold=self.confidence,
                target_sizes=target_sizes,
            )
        except TypeError:
            results = postprocess(
                outputs,
                inputs.get("input_ids"),
                box_threshold=self.confidence,
                text_threshold=self.confidence,
                target_sizes=target_sizes,
            )
        result = results[0]
        boxes = _to_list(result["boxes"])
        scores = _to_list(result["scores"])
        labels = result.get("text_labels", result.get("labels"))
        if labels is None:
            raise RuntimeError("Grounding DINO result did not include text labels.")
        raw_labels = _to_list(labels)

        detections: list[Detection] = []
        for box, score, label in zip(boxes, scores, raw_labels):
            class_id = self._class_id_for_label(label)
            confidence = float(score.item() if hasattr(score, "item") else score)
            detections.append(
                Detection(
                    x1=float(box[0]),
                    y1=float(box[1]),
                    x2=float(box[2]),
                    y2=float(box[3]),
                    confidence=confidence,
                    class_id=class_id,
                    class_name=self.class_names[class_id],
                )
            )
        return _class_agnostic_nms(
            detections,
            iou_threshold=self.nms_iou,
            maximum=self.max_detections,
        )
