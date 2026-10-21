# Edge Litter Detection

[![CI](https://github.com/biolababs/edge-litter-detection/actions/workflows/ci.yml/badge.svg)](https://github.com/biolababs/edge-litter-detection/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-Apache--2.0-4c1.svg)](LICENSE)
[![Model](https://img.shields.io/badge/Detector-RF--DETR%20Nano-7B61FF.svg)](https://github.com/roboflow/rf-detr)

Portable software for real-time litter detection, multiclass classification,
tracking, counting, and human-assisted material separation on edge-AI devices.

The application accepts an image, downloaded video, local camera, or live
stream and produces annotated media, structured JSON evidence, and a durable
offline SQLite record. It can operate as a perception component on a cleanup
or refuse-collection truck while exposing reviewed observations to a larger
fleet platform. The software is independent of the MSc thesis; the thesis uses
this repository as its reference implementation.

## Project status

| Component | Status |
|---|---|
| Image, video, camera, and stream runtime | Implemented |
| Five-class RF-DETR adapter | Implemented |
| Tracking, class stabilization, and counting | Implemented |
| Offline SQLite observation and count store | Implemented |
| Human review and configurable separation guidance | Implemented |
| Vehicle/route metadata and integration outbox | Implemented |
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
- configurable separation-stream guidance for each material class;
- review flags for low-confidence and `other_litter` observations;
- streaming JSON Lines events;
- an end-of-run JSON summary;
- persistent SQLite run, frame-count, review, and integration records;
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
writes timestamped output under `reports/generated/`. It also creates the
offline database at `state/litter-edge.db`; no database server is required.

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

# Truck/route operational context
./startup.sh \
  --source 0 \
  --edge-device-id edge-truck-01 \
  --vehicle-id truck-12 \
  --route-id route-a

# HTTP API
./startup.sh --api

# Counts, review, and integration API; a model is not required
./startup.sh --counts-api
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
| SQLite database | Runs, frame counts, optional detections, review queue, confirmed collections, and integration events |

Every frame event follows
[`schemas/detection-event.schema.json`](schemas/detection-event.schema.json).
Stream credentials and URL query strings are removed from recorded evidence.
Fleet/outbox payloads follow
[`schemas/integration-event.schema.json`](schemas/integration-event.schema.json).

## Persistent operational counts

SQLite persistence is enabled by default:

```text
state/litter-edge.db
```

Inspect aggregate counts:

```bash
python query_counts.py summary
python query_counts.py summary --vehicle-id truck-12 --route-id route-a
python query_counts.py runs --limit 20
python query_counts.py reviews --status pending
python query_counts.py outbox
```

The store uses write-ahead logging so inference and local API readers can use
the database concurrently. Count records survive application and vehicle
restarts. Full per-detection rows are disabled by default to control disk use;
enable them with `./startup.sh --persist-detections`.

The database deliberately separates:

- **observed litter:** model detections and unique tracks;
- **human-reviewed classification:** confirmed, corrected, or rejected review
  items;
- **confirmed collected material:** a separate record submitted by a human,
  arm controller, or sensor-fusion component.

A model detection never becomes a collection claim automatically.

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

Read truck and route counts:

```bash
curl "http://127.0.0.1:8088/v1/counts/summary?vehicle_id=truck-12&route_id=route-a"
curl "http://127.0.0.1:8088/v1/review-queue?status=pending"
curl "http://127.0.0.1:8088/v1/integration/events"
```

Confirm that a detected item was physically collected:

```bash
curl \
  -H "Content-Type: application/json" \
  -d '{
    "run_id": "RUN_ID",
    "track_id": 7,
    "class_name": "plastic",
    "method": "human",
    "confirmed_by": "operator-1",
    "external_reference": "pickup-0001"
  }' \
  http://127.0.0.1:8088/v1/collections
```

Use `method: "arm_controller"` only when a separate controller has positively
confirmed the pickup. Detection alone is not confirmation.

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
        /          |          |           \
     JSONL    JSON summary   SQLite    annotated media
                                |
                    review queue + outbox/API
```

The tracking, counting, event, and API layers are independent of accelerator
hardware. Runtime-specific adapters can be added without rewriting the
application core.

## Cleanup-truck integration

The repository is designed as a perception and evidence component rather than
a standalone robot controller. A typical deployment connects:

```text
truck camera -> edge inference -> SQLite/WAL -> worker display
                         |              |
                         |              +-> fleet API/cloud sync
                         +-> candidate event -> planner -> safety PLC -> arm
                                                      |
                                      pickup confirmation -> SQLite/API
```

The worker display shows the detected class, confidence, track ID, suggested
separation stream, and a red `REVIEW` marker when human judgment is required.
Mappings are operator-configurable in
[`config/separation.yaml`](config/separation.yaml).

The perception process must not directly energize or move a collection arm.
Emergency stops, exclusion zones, proximity sensing, motion limits, interlocks,
and final actuation authority belong to a safety-rated truck controller. See
[Truck integration](docs/TRUCK_INTEGRATION.md).

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
state/               ignored local SQLite operational state
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
