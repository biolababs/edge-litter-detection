from pathlib import Path
from tempfile import TemporaryDirectory
from types import ModuleType
from unittest.mock import patch
import sys
import unittest

from litter_edge.adapters.rfdetr import RFDETRDetector


class FakeArray:
    def __init__(self, values: list[object]) -> None:
        self.values = values

    def tolist(self) -> list[object]:
        return self.values


class FakePredictions:
    xyxy = FakeArray([[1.0, 2.0, 30.0, 40.0]])
    confidence = FakeArray([0.91])
    class_id = FakeArray([3])


class FakeModel:
    def predict(self, frame: object, threshold: float) -> FakePredictions:
        self.threshold = threshold
        return FakePredictions()

    def inference(self, dtype: object) -> None:
        self.inference_dtype = dtype


class FakeFrame:
    def __getitem__(self, key: object) -> "FakeFrame":
        return self

    def copy(self) -> "FakeFrame":
        return self


class RFDETRAdapterTests(unittest.TestCase):
    def test_normalizes_checkpoint_predictions(self) -> None:
        module = ModuleType("rfdetr")
        model = FakeModel()

        class FakeRFDETR:
            @classmethod
            def from_checkpoint(cls, path: str, device: str) -> FakeModel:
                model.path = path
                model.device = device
                return model

        class FakeNano:
            pass

        module.RFDETR = FakeRFDETR
        module.RFDETRNano = FakeNano
        with TemporaryDirectory() as temporary:
            checkpoint = Path(temporary) / "model.pth"
            checkpoint.touch()
            with patch.dict(sys.modules, {"rfdetr": module}):
                detector = RFDETRDetector(
                    model_reference=str(checkpoint),
                    class_names={3: "plastic"},
                    confidence=0.4,
                    device="cpu",
                    optimize=False,
                )
                detections = detector.predict(FakeFrame())

        self.assertEqual(len(detections), 1)
        self.assertEqual(detections[0].bbox, (1.0, 2.0, 30.0, 40.0))
        self.assertEqual(detections[0].class_name, "plastic")
        self.assertEqual(detections[0].confidence, 0.91)
        self.assertEqual(model.threshold, 0.4)
        self.assertEqual(model.device, "cpu")

    def test_enables_current_half_precision_inference_api(self) -> None:
        rfdetr_module = ModuleType("rfdetr")
        torch_module = ModuleType("torch")
        torch_module.float16 = object()
        model = FakeModel()

        class FakeRFDETR:
            @classmethod
            def from_checkpoint(cls, path: str, device: str) -> FakeModel:
                return model

        rfdetr_module.RFDETR = FakeRFDETR
        with TemporaryDirectory() as temporary:
            checkpoint = Path(temporary) / "model.pth"
            checkpoint.touch()
            with patch.dict(
                sys.modules,
                {"rfdetr": rfdetr_module, "torch": torch_module},
            ):
                RFDETRDetector(
                    model_reference=str(checkpoint),
                    class_names={3: "plastic"},
                    confidence=0.4,
                    device="cuda",
                    optimize=True,
                )

        self.assertIs(model.inference_dtype, torch_module.float16)


if __name__ == "__main__":
    unittest.main()
