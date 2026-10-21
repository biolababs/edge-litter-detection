from __future__ import annotations

from contextlib import nullcontext
from types import ModuleType
from unittest.mock import patch
import sys
import unittest

from litter_edge.adapters.omdet_turbo import (
    OmDetTurboDetector,
    _explicit_timm_backbone_config,
    _materialize_meta_buffers,
    _numeric_version,
    _validate_runtime_versions,
)


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
    load_options: dict[str, object] = {}

    @classmethod
    def from_pretrained(
        cls,
        model_reference: str,
        **kwargs: object,
    ) -> "FakeProcessor":
        instance = cls()
        instance.model_reference = model_reference
        cls.load_options = dict(kwargs)
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
    load_options: dict[str, object] = {}

    @classmethod
    def from_pretrained(
        cls,
        model_reference: str,
        **kwargs: object,
    ) -> "FakeModel":
        instance = cls()
        instance.model_reference = model_reference
        cls.load_options = dict(kwargs)
        return instance

    def to(self, device: str) -> None:
        self.device = device

    def eval(self) -> None:
        self.eval_called = True

    def __call__(self, **inputs: object) -> object:
        self.inputs = inputs
        return object()


class FakeBuffer:
    def __init__(self, is_meta: bool) -> None:
        self.is_meta = is_meta


class FakeBufferModule:
    def __init__(self, *, can_initialize: bool = True) -> None:
        self.buffer = FakeBuffer(is_meta=True)
        self.can_initialize = can_initialize

    def buffers(self, recurse: bool = True) -> list[FakeBuffer]:
        del recurse
        return [self.buffer]

    def init_non_persistent_buffers(self) -> None:
        if self.can_initialize:
            self.buffer = FakeBuffer(is_meta=False)


class FakeBufferModel:
    def __init__(self, child: FakeBufferModule) -> None:
        self.child = child

    def modules(self) -> list[object]:
        return [self, self.child]

    def buffers(self, recurse: bool = True) -> list[FakeBuffer]:
        del recurse
        return []

    def named_buffers(self) -> list[tuple[str, FakeBuffer]]:
        return [("backbone.attn_mask", self.child.buffer)]


class OmDetTurboAdapterTests(unittest.TestCase):
    def test_rewrites_timm_backbone_without_remote_repo_lookup(self) -> None:
        rewritten = _explicit_timm_backbone_config(
            {
                "model_type": "omdet-turbo",
                "backbone": "swin_tiny_patch4_window7_224",
                "use_timm_backbone": True,
                "use_pretrained_backbone": False,
                "image_size": 640,
            }
        )

        self.assertNotIn("backbone", rewritten)
        self.assertNotIn("use_timm_backbone", rewritten)
        self.assertEqual(
            rewritten["backbone_config"],
            {
                "model_type": "timm_backbone",
                "backbone": "swin_tiny_patch4_window7_224",
                "out_indices": [1, 2, 3],
                "img_size": 640,
                "always_partition": True,
            },
        )

    def test_parses_framework_versions(self) -> None:
        self.assertEqual(_numeric_version("2.7.0a0+79aa17489c.nv25.04"), (2, 7, 0))

    def test_rejects_transformers_five_with_old_pytorch(self) -> None:
        torch_module = ModuleType("torch")
        torch_module.__version__ = "2.4.0"
        transformers_module = ModuleType("transformers")
        transformers_module.__version__ = "5.20.2"

        with self.assertRaisesRegex(RuntimeError, "PyTorch 2.6 or newer"):
            _validate_runtime_versions(torch_module, transformers_module)

    def test_materializes_non_persistent_meta_buffers(self) -> None:
        child = FakeBufferModule()
        model = FakeBufferModel(child)

        _materialize_meta_buffers(model)

        self.assertFalse(child.buffer.is_meta)

    def test_rejects_meta_buffers_that_cannot_be_materialized(self) -> None:
        child = FakeBufferModule(can_initialize=False)
        model = FakeBufferModel(child)

        with self.assertRaisesRegex(
            RuntimeError,
            "backbone.attn_mask",
        ):
            _materialize_meta_buffers(model)

    def test_normalizes_labels_scores_and_suppresses_duplicates(self) -> None:
        torch_module = ModuleType("torch")
        torch_module.__version__ = "2.7.0"
        torch_module.inference_mode = nullcontext
        torch_module.float16 = object()
        transformers_module = ModuleType("transformers")
        transformers_module.__version__ = "4.57.6"
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
        self.assertEqual(
            FakeProcessor.load_options["revision"],
            "7fe93cecfb770c4d76cf71163956221249cab566",
        )
        self.assertFalse(FakeModel.load_options["trust_remote_code"])
        self.assertTrue(FakeModel.load_options["use_safetensors"])


if __name__ == "__main__":
    unittest.main()
