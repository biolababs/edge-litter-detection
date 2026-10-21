from __future__ import annotations

from contextlib import nullcontext
from numbers import Integral
from typing import Any

from ..schema import Detection
from ..settings import resolve_transformers_model_reference
from .grounding_dino import (
    _class_agnostic_nms,
    _normalize_label,
    _to_list,
)


def _materialize_meta_buffers(model: Any) -> None:
    """Initialize non-persistent buffers left on the meta device."""
    modules = getattr(model, "modules", None)
    named_buffers = getattr(model, "named_buffers", None)
    if not callable(modules) or not callable(named_buffers):
        return

    for module in modules():
        buffers = getattr(module, "buffers", None)
        if not callable(buffers):
            continue
        has_local_meta_buffer = any(
            getattr(buffer, "is_meta", False)
            for buffer in buffers(recurse=False)
        )
        initializer = getattr(module, "init_non_persistent_buffers", None)
        if has_local_meta_buffer and callable(initializer):
            initializer()

    remaining = [
        name
        for name, buffer in named_buffers()
        if getattr(buffer, "is_meta", False)
    ]
    if remaining:
        preview = ", ".join(remaining[:5])
        suffix = "" if len(remaining) <= 5 else ", ..."
        raise RuntimeError(
            "OmDet-Turbo contains unmaterialized model buffers after loading: "
            f"{preview}{suffix}"
        )


class OmDetTurboDetector:
    """Compact open-vocabulary detector loaded through Transformers."""

    backend_name = "omdet_turbo"

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
            from transformers import AutoProcessor, OmDetTurboForObjectDetection
        except ImportError as exc:
            raise RuntimeError(
                "The OmDet-Turbo runtime is not installed. Install the "
                "'public-model' optional dependency."
            ) from exc

        self.torch = torch
        self.device = device
        self.class_names = class_names
        self.class_prompts = class_prompts or {
            class_id: name.replace("_", " ")
            for class_id, name in class_names.items()
        }
        if set(self.class_prompts) != set(self.class_names):
            raise ValueError("OmDet-Turbo prompts must match all class IDs.")
        self.prompt_class_ids = sorted(self.class_names)
        self.prompt_list = [
            self.class_prompts[class_id] for class_id in self.prompt_class_ids
        ]
        self.prompt_to_class_id = {
            _normalize_label(prompt): class_id
            for class_id, prompt in self.class_prompts.items()
        }
        self.fallback_class_id = next(
            (
                class_id
                for class_id, name in self.class_names.items()
                if name == "other_litter"
            ),
            None,
        )
        self.confidence = confidence
        self.nms_iou = nms_iou
        self.max_detections = max_detections
        self.use_autocast = optimize and device.startswith("cuda")

        model_id, revision = resolve_transformers_model_reference(
            self.backend_name,
            model_reference,
        )
        self.processor = AutoProcessor.from_pretrained(
            model_id,
            revision=revision,
            trust_remote_code=False,
        )
        self.model = OmDetTurboForObjectDetection.from_pretrained(
            model_id,
            revision=revision,
            use_safetensors=True,
            trust_remote_code=False,
        )
        _materialize_meta_buffers(self.model)
        self.model.to(device)
        self.model.eval()

    def _class_id_for_label(self, label: object) -> int:
        if isinstance(label, Integral):
            label_index = int(label)
            if 0 <= label_index < len(self.prompt_class_ids):
                return self.prompt_class_ids[label_index]
            if label_index in self.class_names:
                return label_index
        else:
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
        if self.fallback_class_id is not None:
            return self.fallback_class_id
        raise RuntimeError(f"OmDet-Turbo returned an unmapped label: {label!r}")

    def predict(self, frame_bgr: Any) -> list[Detection]:
        frame_rgb = frame_bgr[:, :, ::-1].copy()
        inputs = self.processor(
            images=frame_rgb,
            text=self.prompt_list,
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
                text_labels=[self.prompt_list],
                target_sizes=target_sizes,
                threshold=self.confidence,
                nms_threshold=self.nms_iou,
                max_num_det=self.max_detections,
            )
        except TypeError:
            try:
                results = postprocess(
                    outputs,
                    text_labels=[self.prompt_list],
                    target_sizes=target_sizes,
                    score_threshold=self.confidence,
                    nms_threshold=self.nms_iou,
                )
            except TypeError:
                results = postprocess(
                    outputs,
                    classes=[self.prompt_list],
                    target_sizes=target_sizes,
                    score_threshold=self.confidence,
                    nms_threshold=self.nms_iou,
                )
        result = results[0]
        boxes = _to_list(result["boxes"])
        scores = _to_list(result["scores"])
        labels = result.get("labels")
        if labels is None:
            labels = result.get("text_labels")
        if labels is None:
            labels = result.get("classes")
        if labels is None:
            raise RuntimeError("OmDet-Turbo result did not include labels.")
        raw_labels = _to_list(labels)

        detections: list[Detection] = []
        for box, score, label in zip(
            boxes,
            scores,
            raw_labels,
            strict=True,
        ):
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
