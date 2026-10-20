from __future__ import annotations

import unittest
from pathlib import Path

from litter_edge.export import build_export_arguments


class ExportArgumentsTests(unittest.TestCase):
    def test_onnx_uses_documented_fp32_arguments(self) -> None:
        arguments = build_export_arguments(
            export_format="onnx",
            precision="fp32",
            output_dir=Path("models"),
            image_size=560,
        )

        self.assertEqual(arguments["format"], "onnx")
        self.assertEqual(arguments["shape"], (560, 560))
        self.assertNotIn("fp16", arguments)
        self.assertNotIn("quantization", arguments)

    def test_onnx_rejects_fp16(self) -> None:
        with self.assertRaisesRegex(ValueError, "ONNX export uses FP32"):
            build_export_arguments(
                export_format="onnx",
                precision="fp16",
                output_dir=Path("models"),
                image_size=560,
            )

    def test_tensorrt_sets_fp16_flag(self) -> None:
        arguments = build_export_arguments(
            export_format="tensorrt",
            precision="fp16",
            output_dir=Path("models"),
            image_size=560,
        )

        self.assertIs(arguments["fp16"], True)

    def test_tensorrt_rejects_int8(self) -> None:
        with self.assertRaisesRegex(ValueError, "TensorRT INT8"):
            build_export_arguments(
                export_format="tensorrt",
                precision="int8",
                output_dir=Path("models"),
                image_size=560,
            )

    def test_tflite_int8_requires_calibration_data(self) -> None:
        with self.assertRaisesRegex(ValueError, "calibration-data"):
            build_export_arguments(
                export_format="tflite",
                precision="int8",
                output_dir=Path("models"),
                image_size=560,
            )

        arguments = build_export_arguments(
            export_format="tflite",
            precision="int8",
            output_dir=Path("models"),
            image_size=560,
            calibration_data="data/calibration",
        )
        self.assertEqual(arguments["quantization"], "int8")
        self.assertEqual(arguments["calibration_data"], "data/calibration")


if __name__ == "__main__":
    unittest.main()
