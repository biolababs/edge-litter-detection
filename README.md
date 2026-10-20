# Edge Litter Detection

[![CI](https://github.com/biolababs/edge-litter-detection/actions/workflows/ci.yml/badge.svg)](https://github.com/biolababs/edge-litter-detection/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-Apache--2.0-4c1.svg)](LICENSE)
[![Model](https://img.shields.io/badge/Detector-RF--DETR%20Nano-7B61FF.svg)](https://github.com/roboflow/rf-detr)

Portable software for real-time litter detection, multiclass classification,
tracking, and counting on edge-AI devices.

The application accepts an image, downloaded video, local camera, or live
stream and produces annotated media plus structured JSON evidence. The
software is independent of the MSc thesis; the thesis uses this repository as
its reference implementation.

## Project status

| Component | Status |
|---|---|
| Image, video, camera, and stream runtime | Implemented |
| Five-class RF-DETR adapter | Implemented |
| Tracking, class stabilization, and counting | Implemented |
| Source discovery and input probing | Implemented |
| CLI, HTTP API, container, tests, and schemas | Implemented |
| Trained litter checkpoint | Pending data and training |
| Accuracy and edge-device results | Pending testing |

> [!IMPORTANT]
> A trained five-class litter checkpoint is not distributed yet. The
> application code can be installed and its input pipeline can be tested now,
> but valid litter inference requires a compatible trained checkpoint. The
> repository does not relabel a generic COCO model as a litter detector.

## What the application returns

- bounding boxes, confidence scores, and litter classes;
- five classes: `glass`, `metal`, `paper_cardboard`, `plastic`, and
  `other_litter`;
- visible counts for each frame;
- stable track IDs across video frames;
- unique confirmed-track counts for the active run;
- streaming JSON Lines events;
- an end-of-run JSON summary;
- optional annotated images and videos.

One object visible in 100 frames is normally counted once, not 100 times. See
[Counting semantics](docs/COUNTING.md) for limitations and exact definitions.

## Quick start

Clone the repository and run the automated launcher:

```bash
git clone https://github.com/biolababs/edge-litter-detection.git
cd edge-litter-detection
./startup.sh
```

The launcher requires Python 3.10 or newer and automatically selects an
available Python 3.10–3.12 interpreter.

The launcher creates the Python environment, installs the application,
discovers a camera or media file, validates the source, runs inference, and
writes timestamped output under `reports/generated/`.

After the project checkpoint is released, its URL and checksum will be recorded
in `config/model-release.json`. A fresh clone will then need no model flags.

If the default checkpoint is absent, the interactive launcher asks for its
path. A published checkpoint can be installed and verified in the same command:

```bash
./startup.sh \
  --model-url "$LITTER_MODEL_URL" \
  --model-sha256 "$LITTER_MODEL_SHA256"
```

Until the project checkpoint is published, supply a compatible trained
checkpoint:

```bash
./startup.sh --model /path/to/rfdetr-nano-litter.pth
```

Select an input with the same launcher:

```bash
# Auto-detect the first working camera or file under media/
./startup.sh

# Specific attached camera
./startup.sh --source 0

# Downloaded image
./startup.sh --source ./media/litter.jpg

# Downloaded video
./startup.sh --source ./media/litter.mp4

# Live stream
export LITTER_STREAM_URL="rtsp://camera-host/live"
./startup.sh --source "$LITTER_STREAM_URL"

# Headless edge device
./startup.sh --source "$LITTER_STREAM_URL" --no-display

# HTTP API
./startup.sh --api
```

Press `q` in the display window or `Ctrl+C` in the terminal to finish a live
run. Use `./startup.sh --help` for all automation options. Advanced users can
still call the individual Python commands directly. See
[Input sources](docs/INPUT_SOURCES.md).

## Output contract

| Output | Purpose |
|---|---|
| Annotated image/video | Visual boxes, labels, confidence, and track IDs |
| JSONL event stream | One durable event for every processed frame |
| JSON summary | Run metadata, throughput, peak visible counts, and unique counts |

Every frame event follows
[`schemas/detection-event.schema.json`](schemas/detection-event.schema.json).
Stream credentials and URL query strings are removed from recorded evidence.

## HTTP API

Start the single-image API through the same launcher:

```bash
./startup.sh --api
```

Use `--model`, `--model-url`, and `--model-sha256` in the same way as media
inference.

Check service state:

```bash
curl http://127.0.0.1:8088/healthz
curl http://127.0.0.1:8088/readyz
```

Detect one image:

```bash
curl \
  -H "Content-Type: image/jpeg" \
  --data-binary @media/litter.jpg \
  http://127.0.0.1:8088/v1/detect
```

HTTP requests are independent images. Stateful tracking and unique-session
counting use the CLI.

## Container

The included container is a CPU/reference API deployment:

```bash
docker compose build
docker compose up
```

Mount the checkpoint under `models/`. Accelerator deployments should use a
vendor-compatible PyTorch base environment rather than treating the CPU image
as an optimized NVIDIA, AMD, or Jetson image.

## Train the litter model

Prepare YOLO- or COCO-format annotations as documented in
[`data/README.md`](data/README.md):

```bash
python -m pip install -e ".[runtime,train]"

python train.py \
  --model rfdetr-nano \
  --data data/litter
```

Training is intended for a workstation or cloud GPU. The trained artifact,
class schema, dataset version, and threshold configuration must remain
traceable. “YOLO format” here describes only an annotation layout; the detector
implemented by this repository remains RF-DETR Nano.

## Evaluate accuracy

Evaluate the single trained checkpoint on a frozen held-out split:

```bash
python evaluate.py \
  --weights runs/litter/rfdetr-nano-baseline/checkpoint_best_ema.pth \
  --data data/litter \
  --split test \
  --output reports/generated/detection-accuracy.json
```

Evaluate frame and unique-session count accuracy:

```bash
python evaluate_counts.py \
  --events reports/generated/litter-video.jsonl \
  --ground-truth data/count-ground-truth.json \
  --output reports/generated/count-accuracy.json
```

These commands evaluate whether the RF-DETR implementation satisfies the
litter use case. They do not compare model families.

## Export

Example ONNX export:

```bash
python -m pip install "rfdetr[onnx]>=1.10,<1.11"

python export_model.py \
  --weights runs/litter/rfdetr-nano-baseline/checkpoint_best_ema.pth \
  --format onnx \
  --precision fp32
```

The export command also exposes TensorRT and TFLite. Every exported artifact
must be checked for accuracy retention and target-runtime compatibility before
deployment.

## Architecture

```text
image / video / camera / stream
                |
                v
          RF-DETR adapter
                |
                v
      standard Detection records
                |
                v
       class-stabilized tracking
                |
                v
     visible + unique run counts
        /           |          \
     JSONL      JSON summary   annotated media
```

The tracking, counting, event, and API layers are independent of accelerator
hardware. Runtime-specific adapters can be added without rewriting the
application core.

## Supported deployment profiles

| Target | Primary path | Status |
|---|---|---|
| CPU | RF-DETR/PyTorch | Development and functional testing |
| NVIDIA CUDA | RF-DETR/PyTorch CUDA | Adapter implemented |
| AMD ROCm / Strix Halo | RF-DETR/PyTorch ROCm | Code path ready; validation pending |
| Jetson Orin 8 GB | JetPack-compatible runtime | Read-only inventory complete; deployment pending |
| ONNX/OpenVINO/TensorRT | Exported artifact plus adapter | Target integration pending |

Hardware results are device-specific and are never generalized across targets.

## Software and thesis separation

This repository has two related but distinct deliverables:

- **Reusable software:** source code, tests, schemas, deployment examples, and
  software documentation under Apache-2.0.
- **Research work:** the MSc manuscript, dataset, trained weights, experiments,
  and measured results, each with separate review and release requirements.

The software can be cloned and deployed without the thesis. The thesis records
how a versioned commit, dataset, checkpoint, and device configuration are
evaluated. See [Software and research](docs/SOFTWARE_AND_RESEARCH.md).

## Repository structure

```text
src/litter_edge/     application package
config/              class and runtime configuration
schemas/             stable JSON integration contracts
deploy/              CPU, NVIDIA, AMD, and service examples
docs/                operational and research documentation
tests/               dependency-light unit tests
thesis/              prospective MSc manuscript
```

## Validation

```bash
make validate
```

This runs unit tests, release checks, and command-line smoke checks. Target
accuracy and real-time performance remain pending until the dataset, trained
checkpoint, and authorized hardware test window exist.

## Security and privacy

The project detects litter, not people. Face identification, person
re-identification, license-plate recognition, behavior scoring, and automated
enforcement are out of scope.

Do not commit stream credentials, private imagery, datasets, model weights, or
raw device inventories. The API binds to localhost by default and has no
built-in authentication; place it behind an authenticated gateway before
network exposure. See [Security](SECURITY.md).

## License and citation

The software and software documentation are licensed under Apache-2.0. Dataset,
model-weight, generated-result, and academic-manuscript rights remain separate;
see [License notice](LICENSE-NOTICE.md).

Citation metadata is provided in [`CITATION.cff`](CITATION.cff).
