from __future__ import annotations

from pathlib import Path
from typing import Any

from ..schema import Detection


class RFDETRDetector:
    backend_name = "rfdetr"

    def __init__(
        self,
        model_reference: str,
        class_names: dict[int, str],
        confidence: float,
        device: str,
        optimize: bool = True,
    ) -> None:
        try:
            from rfdetr import RFDETR
        except ImportError as exc:
            raise RuntimeError(
                "RF-DETR is not installed. Install the 'rfdetr' optional "
                "dependency for this deployment profile."
            ) from exc

        self.class_names = class_names
        self.confidence = confidence
        model_path = Path(model_reference)
        if model_path.is_file():
            self.model = RFDETR.from_checkpoint(str(model_path), device=device)
        else:
            raise FileNotFoundError(
                f"RF-DETR checkpoint not found: {model_reference}. Train the "
                "litter model before running inference."
            )

        if optimize and device.startswith("cuda"):
            import torch

            self.model.inference(dtype=torch.float16)

    def predict(self, frame_bgr: Any) -> list[Detection]:
        frame_rgb = frame_bgr[:, :, ::-1].copy()
        predictions = self.model.predict(frame_rgb, threshold=self.confidence)
        boxes = predictions.xyxy.tolist()
        confidences = predictions.confidence.tolist()
        class_ids = predictions.class_id.tolist()

        output: list[Detection] = []
        for box, confidence, class_id in zip(boxes, confidences, class_ids):
            numeric_id = int(class_id)
            if numeric_id not in self.class_names:
                raise RuntimeError(
                    f"Checkpoint produced class ID {numeric_id}, which is not "
                    "present in the configured litter taxonomy."
                )
            output.append(
                Detection(
                    x1=float(box[0]),
                    y1=float(box[1]),
                    x2=float(box[2]),
                    y2=float(box[3]),
                    confidence=float(confidence),
                    class_id=numeric_id,
                    class_name=self.class_names[numeric_id],
                )
            )
        return output
