# Portable deployment

## Supported architecture

The application core is hardware-neutral. Model adapters produce the same
`Detection` schema, and tracking/counting runs in ordinary Python. A deployment
profile selects the accelerator-specific PyTorch build and model runtime.

| Target | Initial runtime | Device value | Status |
|---|---|---|---|
| CPU development host | RF-DETR/PyTorch CPU | `cpu` | runnable after dependencies and weights exist |
| NVIDIA CUDA workstation | RF-DETR/PyTorch CUDA | `cuda` | supported by the primary adapter |
| AMD ROCm / Strix Halo | RF-DETR/PyTorch ROCm | `cuda` | code path ready; hardware benchmark pending |
| Jetson Orin Nano 8 GB Super | JetPack-compatible runtime | `cuda` | inventory complete; deployment not authorized |
| ONNX Runtime / OpenVINO | exported RF-DETR ONNX | provider-specific | adapter pending validated output contract |
| TensorRT | optimized target engine | target-specific | adapter pending target validation |

PyTorch uses the `cuda` device name for ROCm accelerators. This does not mean an
AMD system uses NVIDIA CUDA; it is PyTorch's compatibility-facing device API.

## Local CLI

Install the hardware-appropriate PyTorch build first. Then:

```bash
python -m pip install -e ".[runtime,rfdetr]"

python infer.py \
  --model models/rfdetr-nano-litter.pth \
  --source sample.mp4 \
  --annotated-output reports/generated/sample-annotated.mp4 \
  --events-output reports/generated/sample-events.jsonl \
  --output reports/generated/sample-summary.json
```

The trained litter checkpoint is intentionally not present yet.

## Image API

```bash
python -m pip install -e ".[runtime,rfdetr,api]"
LITTER_MODEL=models/rfdetr-nano-litter.pth python serve.py
```

Health:

```bash
curl http://127.0.0.1:8088/healthz
curl http://127.0.0.1:8088/readyz
```

Detect one image:

```bash
curl \
  -H "Content-Type: image/jpeg" \
  --data-binary @sample.jpg \
  http://127.0.0.1:8088/v1/detect
```

Independent HTTP images return per-image counts. Use the CLI for stateful video
tracking and unique-session counts.

## Container

The root Dockerfile is a portable CPU/reference image:

```bash
docker compose build
docker compose up
```

Mount the trained checkpoint under `models/`. Do not treat this CPU image as an
optimized Jetson or ROCm image.

For NVIDIA or AMD, start from a vendor-supported container or environment that
already contains the correct PyTorch accelerator build, then install this
package's `runtime`, `api`, and `rfdetr` extras. Preserve a manifest containing
the base image digest, driver/runtime versions, model checksum, configuration,
and Git revision.

## Portability contract

An RF-DETR runtime adapter needs only:

```python
class Detector:
    backend_name: str

    def predict(self, frame_bgr) -> list[Detection]:
        ...
```

It must return pixel-coordinate `xyxy` boxes, confidence, class ID, and class
name. No tracking or counting code should be copied into an adapter.

## Official platform references

- RF-DETR installation and inference: https://rfdetr.roboflow.com/latest/
- RF-DETR export formats: https://rfdetr.roboflow.com/latest/learn/export/
- AMD Ryzen/ROCm PyTorch guidance:
  https://rocm.docs.amd.com/projects/radeon-ryzen/en/latest/docs/install/installrad/native_linux/install-pytorch.html
- NVIDIA JetPack: https://developer.nvidia.com/embedded/jetpack
