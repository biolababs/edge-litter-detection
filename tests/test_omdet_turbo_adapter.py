from __future__ import annotations

from contextlib import nullcontext
from types import ModuleType
from unittest.mock import patch
import sys
import unittest

from litter_edge.adapters.omdet_turbo import OmDetTurboDetector


class FakeFrame:
    shape = (100, 200, 3)

    def __getitem__(self, key: object) -> "FakeFrame":
        return self

    def copy(self) -> "FakeFrame":
        return self


class FakeInputs(dict):
    def to(self, device: str) -> "FakeInputs":
        self.device = device
        return self


class FakeProcessor:
    @classmethod
    def from_pretrained(cls, model_reference: str) -> "FakeProcessor":
        instance = cls()
        instance.model_reference = model_reference
        return instance

    def __call__(
        self,
        images: object,
        text: list[str],
        return_tensors: str,
    ) -> FakeInputs:
        self.images = images
        self.text = text
        self.return_tensors = return_tensors
        return FakeInputs(pixel_values=[1])

    def post_process_grounded_object_detection(
        self,
        outputs: object,
        text_labels: list[list[str]],
        target_sizes: list[tuple[int, int]],
        threshold: float,
        nms_threshold: float,
        max_num_det: int,
    ) -> list[dict[str, object]]:
        self.text_labels = text_labels
        self.target_sizes = target_sizes
        self.threshold = threshold
        self.nms_threshold = nms_threshold
        self.max_num_det = max_num_det
        return [
            {
                "boxes": [
                    [1.0, 2.0, 31.0, 42.0],
                    [2.0, 3.0, 30.0, 41.0],
                    [100.0, 20.0, 140.0, 70.0],
                ],
                "scores": [0.92, 0.81, 0.88],
                "labels": [0, 2, 1],
                "text_labels": [
                    "discarded plastic bottle",
                    "discarded trash or litter",
                    "discarded battery",
                ],
            }
        ]


class FakeModel:
    @classmethod
    def from_pretrained(cls, model_reference: str) -> "FakeModel":
        instance = cls()
        instance.model_reference = model_reference
        return instance

    def to(self, device: str) -> None:
        self.device = device

    def eval(self) -> None:
        self.eval_called = True

    def __call__(self, **inputs: object) -> object:
        self.inputs = inputs
        return object()


class OmDetTurboAdapterTests(unittest.TestCase):
    def test_normalizes_labels_scores_and_suppresses_duplicates(self) -> None:
        torch_module = ModuleType("torch")
        torch_module.inference_mode = nullcontext
        torch_module.float16 = object()
        transformers_module = ModuleType("transformers")
        transformers_module.AutoProcessor = FakeProcessor
        transformers_module.OmDetTurboForObjectDetection = FakeModel

        with patch.dict(
            sys.modules,
            {
                "torch": torch_module,
                "transformers": transformers_module,
            },
        ):
            detector = OmDetTurboDetector(
                model_reference="omlab/omdet-turbo-swin-tiny-hf",
                class_names={
                    0: "plastic_bottle",
                    1: "battery",
                    2: "other_litter",
                },
                class_prompts={
                    0: "discarded plastic bottle",
                    1: "discarded battery",
                    2: "discarded trash or litter",
                },
                confidence=0.35,
                device="cpu",
                optimize=False,
                nms_iou=0.6,
            )
            detections = detector.predict(FakeFrame())

        self.assertEqual(
            [detection.class_name for detection in detections],
            ["plastic_bottle", "battery"],
        )
        self.assertEqual(detections[0].bbox, (1.0, 2.0, 31.0, 42.0))
        self.assertEqual(detector.processor.target_sizes, [(100, 200)])
        self.assertEqual(detector.processor.threshold, 0.35)
        self.assertEqual(detector.processor.max_num_det, 100)
        self.assertEqual(detector.model.device, "cpu")
        self.assertTrue(detector.model.eval_called)


if __name__ == "__main__":
    unittest.main()
