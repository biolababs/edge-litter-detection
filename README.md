# Edge Litter Detection, Classification, Tracking, and Counting

Portable edge-AI software for locating litter, assigning a litter class, and
counting objects in images and video.

Public repository:
`github.com/biolababs/edge-litter-detection`

## What it produces

For each frame, the application returns:

- bounding boxes and confidence scores;
- multiclass labels: glass, metal, paper/cardboard, plastic, and other litter;
- the number of each class visible in the current frame;
- stable track IDs across video frames;
- unique counts per class for the current inspection session;
- JSON Lines events, an end-of-run JSON summary, and optional annotated media.

The project counts tracks rather than summing frame detections, so one object
visible for 100 frames is normally counted once. See `docs/COUNTING.md` for
the exact semantics and limitations.

## Model and hardware policy

RF-DETR Nano is the implementation model. This project does not compare model
families. The application core is runtime- and hardware-neutral:

```text
image / video / camera / RTSP
             |
             v
  model + accelerator adapter
             |
             v
 standard Detection records
             |
             v
 class stabilization + tracking
             |
             v
 visible counts + unique session counts
             |
             +--> JSONL events
             +--> JSON summary
             `--> annotated image/video
```

The same tracking, counting, evidence, and API code can run with:

- CPU for development and functional testing;
- NVIDIA CUDA on workstations;
- AMD ROCm, including a compatible Strix Halo/Ryzen AI Max environment;
- NVIDIA Jetson after a target-compatible runtime is validated;
- future ONNX Runtime, OpenVINO, or TensorRT adapters without changing the
  counting core.

Hardware results are reported separately. A Jetson number is never presented as
an AMD, CPU, or general edge-device result.

## Current status

- Detection/classification adapter contract: implemented.
- RF-DETR Nano PyTorch adapter: implemented.
- Class-stabilized IoU tracking and unique-session counting: implemented.
- Image/video/camera/stream CLI: implemented.
- Single-image HTTP API: implemented.
- CPU reference container and deployment profiles: implemented.
- Jetson Orin Nano 8 GB Super inventory: completed read-only.
- Data collection, litter-model training, target validation, and final
  results: pending.

No trained litter checkpoint or performance claim exists yet.

## Install

Use Python 3.10 or newer. Install the PyTorch build appropriate for the target
first: CPU, NVIDIA CUDA, AMD ROCm, or NVIDIA JetPack.

Primary RF-DETR runtime:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[runtime,rfdetr]"
```

Add the API:

```bash
python -m pip install -e ".[runtime,rfdetr,api]"
```

## Detect, classify, and count video

After training or supplying a compatible litter checkpoint:

```bash
python infer.py \
  --model models/rfdetr-nano-litter.pth \
  --source sample.mp4 \
  --annotated-output reports/generated/sample-annotated.mp4 \
  --events-output reports/generated/sample-events.jsonl \
  --output reports/generated/sample-summary.json
```

Valid sources include an image, video, camera index such as `0`, or a stream
URL. Use `--no-track` when only independent frame counts are needed.

## HTTP API

```bash
LITTER_MODEL=models/rfdetr-nano-litter.pth python serve.py
```

The API listens on port `8088` by default:

```bash
curl http://127.0.0.1:8088/healthz
curl http://127.0.0.1:8088/readyz

curl \
  -H "Content-Type: image/jpeg" \
  --data-binary @sample.jpg \
  http://127.0.0.1:8088/v1/detect
```

HTTP requests are independent images and return per-image counts. Use the CLI
for stateful video tracking and unique-session counts.

## Container

The root Dockerfile is a CPU/reference deployment:

```bash
docker compose build
docker compose up
```

Mount the trained checkpoint under `models/`. NVIDIA, AMD, and Jetson
deployments must use an accelerator-compatible PyTorch base environment; see
`docs/DEPLOYMENT.md`.

## Train

Prepare the data in the RF-DETR-supported YOLO or COCO layout described in
`data/README.md`, then:

```bash
python -m pip install -e ".[runtime,train]"

python train.py \
  --model rfdetr-nano \
  --data data/litter
```

Training belongs on a workstation or cloud GPU, not the shared 8 GB Jetson.

## Evaluate accuracy

Evaluate the one trained RF-DETR Nano checkpoint on the frozen held-out split:

```bash
python evaluate.py \
  --weights runs/litter/rfdetr-nano-baseline/checkpoint_best_ema.pth \
  --data data/litter \
  --split test \
  --output reports/generated/detection_accuracy.json
```

Evaluate visible and unique-session count accuracy after annotating the
representative video subset:

```bash
python evaluate_counts.py \
  --events reports/generated/sample-events.jsonl \
  --ground-truth data/count-ground-truth.json \
  --output reports/generated/count_accuracy.json
```

Start from `data/count-ground-truth.example.json`. These commands evaluate the
single litter use case; they do not rank models.

## Export

RF-DETR supports portable export targets through optional dependencies:

```bash
python -m pip install "rfdetr[onnx]"

python export_model.py \
  --weights runs/litter/rfdetr-nano-baseline/checkpoint_best_ema.pth \
  --format onnx \
  --precision fp32
```

TensorRT and TFLite exports are also exposed by the command. ONNX can be used
with a validated OpenVINO integration. An export is not considered deployable
until its output contract and accuracy are validated on the target runtime.

## Validate

```bash
PYTHONPATH=src python -m unittest discover -s tests -v
python scripts/validate_release.py
```

## Repository map

- `src/litter_edge/adapters/`: model and accelerator integration boundary.
- `src/litter_edge/tracking.py`: class-stabilized tracking and unique counting.
- `src/litter_edge/runtime.py`: image/video/camera/stream application.
- `src/litter_edge/evaluate.py`: held-out RF-DETR accuracy evaluation.
- `src/litter_edge/evaluate_counts.py`: visible/session count evaluation.
- `src/litter_edge/api.py`: single-image HTTP API.
- `schemas/detection-event.schema.json`: stable frame-event integration
  contract.
- `config/classes.yaml`: versioned litter taxonomy.
- `config/project.yaml`: experiment and runtime defaults.
- `deploy/profiles/`: CPU, NVIDIA CUDA, and AMD ROCm examples.
- `docs/`: counting, deployment, data, experiment, and publication plans.
- `thesis/`: prospective MSc manuscript with results explicitly pending.

## Security, privacy, and release status

The software detects litter, not people. Face identification, person tracking,
license-plate recognition, behavior scoring, and automated enforcement are out
of scope.

The historical notebooks outside this repository contained a Roboflow
credential. It must be revoked before any historical material is published.
Data, model weights, and generated reports are excluded from Git by default.

The software and software documentation are licensed under Apache-2.0. Dataset,
model-weight, generated-result, and academic-manuscript rights remain separate;
see `LICENSE-NOTICE.md`.
