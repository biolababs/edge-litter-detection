# Portable deployment

## Reference architecture

The detector adapter returns a hardware-neutral `Detection` record. Tracking,
counting, SQLite persistence, review, and integration logic are shared across
all devices.

| Target | Reference runtime | Device value | Status |
|---|---|---|---|
| CPU host | PyTorch | `cpu` | Functional reference path |
| NVIDIA CUDA | Vendor PyTorch | `cuda` | Code path implemented; benchmark required |
| AMD ROCm / Strix Halo | Vendor PyTorch | `cuda` | Code path implemented; benchmark required |
| Jetson Orin 8 GB | JetPack-compatible PyTorch or optimized platform service | `cuda` or service-specific | Deployment pending authorized maintenance window |
| Target export | ONNX/OpenVINO/TensorRT adapter | provider-specific | Optional optimization |

PyTorch exposes ROCm accelerators through its `cuda` device API. This does not
mean an AMD computer uses NVIDIA CUDA.

## Normal installation

```bash
./startup.sh --source sample.mp4
```

The launcher currently uses the Grounding DINO bootstrap so a clean clone is
functional while the project RF-DETR checkpoint is pending. Both the bootstrap
and the selected release path fetch and cache their model automatically.

The public profile requires internet access only for initial package/model
download. Input media, counts, and output evidence remain local unless the
deployer adds an external integration worker.

## Accelerator environments

For NVIDIA, AMD, or Jetson:

1. create or select a vendor-supported Python environment;
2. install the correct PyTorch build for the driver/platform;
3. run the launcher with that interpreter:

```bash
LITTER_PYTHON=/path/to/vendor/environment/bin/python \
  ./startup.sh --source 0 --device auto
```

The launcher refuses to create a generic first-time environment on detected
Jetson systems. This protects the JetPack-compatible software stack and avoids
changing a shared device unexpectedly.

## Dashboard and API

```bash
./startup.sh --dashboard --backend omdet_turbo --device auto
```

Open `http://127.0.0.1:8088` locally. For remote administration, forward that
localhost port through a secure tunnel or authenticated gateway.

Health and readiness:

```bash
curl http://127.0.0.1:8088/healthz
curl http://127.0.0.1:8088/readyz
```

Single-image detection:

```bash
curl \
  -H "Content-Type: image/jpeg" \
  --data-binary @sample.jpg \
  http://127.0.0.1:8088/v1/detect
```

Independent HTTP images return per-image visible counts. Use the streaming CLI
or dashboard stream endpoint for tracking and unique run counts.

Start a server-side source:

```bash
curl \
  -H "Content-Type: application/json" \
  -d '{
    "source": "0",
    "edge_device_id": "edge-truck-01",
    "vehicle_id": "truck-12",
    "route_id": "route-a"
  }' \
  http://127.0.0.1:8088/v1/streams
```

The returned session ID addresses status, annotated-frame, and stop endpoints.
The default concurrency limit is one active stream.

## Counts and integration API

```bash
./startup.sh --counts-api
```

This mode does not load or require a detector. It exposes the stored runs,
aggregate counts, review queue, collection confirmations, and integration
outbox.

## Container

```bash
docker compose build
docker compose up
```

The Compose file persists:

- operational SQLite state in `litter-state`; and
- the downloaded public-model cache in `litter-model-cache`.

The included image is a CPU reference. For accelerated deployments, start from
a vendor-supported image containing the correct PyTorch runtime, then install
this project's `runtime-headless`, `public-model`, and `api` extras.

## Selected RF-DETR release path

```bash
./startup.sh --backend rfdetr --source sample.mp4
```

Before publication, this command correctly fails unless a compatible local
checkpoint or explicit verified download is supplied. After maintainers publish
`config/model-release.json`, the same command downloads and verifies the
project checkpoint automatically.

No deployment user is expected to train.

## Adapter contract

```python
class Detector:
    backend_name: str

    def predict(self, frame_bgr) -> list[Detection]:
        ...
```

Adapters return pixel-coordinate `xyxy` boxes, confidence, class ID, and class
name. They do not duplicate tracking, counting, persistence, or integration
logic.

## Deployment evidence

Preserve a manifest containing:

- Git revision;
- model ID or artifact checksum;
- class/prompt and separation configuration;
- base image or environment versions;
- driver and accelerator runtime versions;
- threshold configuration;
- target-device accuracy, count error, latency, memory, power, and thermal
  evidence.

## Platform references

- Transformers Grounding DINO:
  https://huggingface.co/docs/transformers/model_doc/grounding-dino
- RF-DETR: https://rfdetr.roboflow.com/
- AMD PyTorch guidance:
  https://rocm.docs.amd.com/projects/radeon-ryzen/en/latest/docs/install/installrad/native_linux/install-pytorch.html
- NVIDIA JetPack: https://developer.nvidia.com/embedded/jetpack
