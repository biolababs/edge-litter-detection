# Edge Litter Detection

[![CI](https://github.com/biolababs/edge-litter-detection/actions/workflows/ci.yml/badge.svg)](https://github.com/biolababs/edge-litter-detection/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/Code-Apache--2.0-4c1.svg)](LICENSE)
[![Bootstrap model](https://img.shields.io/badge/Bootstrap-Grounding%20DINO%20Tiny-6C63FF.svg)](https://huggingface.co/IDEA-Research/grounding-dino-tiny)

A reusable edge-AI application that detects, classifies, tracks, and counts
visible litter from images, videos, attached cameras, and live streams.

The current bootstrap installation uses the public
[`IDEA-Research/grounding-dino-tiny`](https://huggingface.co/IDEA-Research/grounding-dino-tiny)
open-vocabulary model. It downloads automatically on first use, requires no API
key, and does not require users to collect data or train a model before running
the application. This proves the complete application path; it is not presented
as the final production-accuracy model.

An additional no-training backend,
[`omlab/omdet-turbo-swin-tiny-hf`](https://huggingface.co/omlab/omdet-turbo-swin-tiny-hf),
is available for acceptance screening. OmDet-Turbo Tiny is a compact
Apache-2.0 open-vocabulary detector that returns confidence-scored boxes:

```bash
./startup.sh --backend omdet_turbo --demo
```

It uses backend-specific object prompts while preserving the same stable class
IDs, tracker, counts, SQLite records, review queue, and APIs.

The selected release architecture is a project-maintained, litter-specific
RF-DETR Nano checkpoint. Maintainers train and validate it centrally, publish
versioned weights and a SHA-256 digest, and update the release manifest. Once
published, ordinary users will continue to use the same one-command launcher;
they will not train a model.

The software is designed as a practical perception component for cleanup
vehicles, refuse-collection trucks, fixed monitoring points, and
human-assisted sorting workflows. It stores durable operational counts in
SQLite and exposes review and integration interfaces for a larger system.

## Why this is not limited to five classes

The earlier five-class taxonomy belonged to the MSc research plan. It was too
narrow for a reusable product and depended on a custom trained checkpoint.

The default operational catalog now contains 16 litter categories:

| Category | Suggested workflow |
|---|---|
| `plastic_bottle` | Plastic stream |
| `glass_bottle` | Glass stream |
| `metal_can` | Metal stream |
| `paper` | Fibre stream |
| `cardboard` | Fibre stream |
| `plastic_bag` | Film-plastic stream |
| `food_wrapper` | Manual sort |
| `disposable_cup` | Manual sort |
| `cigarette_butt` | Residual waste |
| `food_waste` | Organics stream |
| `textile` | Textile stream |
| `tire` | Tire recovery |
| `battery` | Hazardous-waste review |
| `electronic_waste` | E-waste review |
| `broken_glass` | Hazardous-glass review |
| `other_litter` | Manual review |

These are stable product output names. During the bootstrap phase, edit
[`config/classes.yaml`](config/classes.yaml) to add, remove, rename, or improve
text prompts without retraining Grounding DINO. A released closed-set checkpoint
supports only the class schema recorded with that checkpoint. Edit
[`config/separation.yaml`](config/separation.yaml) to match the operator's
local sorting policy.

Visual appearance does not always reveal material composition. Low-confidence,
hazardous, and ambiguous detections are therefore flagged for human review.

## Quick start

```bash
git clone https://github.com/biolababs/edge-litter-detection.git
cd edge-litter-detection
./startup.sh
```

That single command:

1. creates an isolated Python environment;
2. installs the runtime and current bootstrap-model dependencies;
3. finds an attached camera or a media file under `media/`;
4. downloads and caches the model on first use;
5. runs detection, classification, tracking, and counting;
6. writes JSON evidence and annotated output; and
7. persists counts to `state/litter-edge.db`.

Python 3.10–3.14 is required. The first run needs internet access to install
packages and download the model. Later runs use the local environment
and model cache.

Run a self-contained functional demonstration when no camera or local media is
ready:

```bash
./startup.sh --demo
```

This downloads a small selection of public TACO litter images into the ignored
`media/taco-demo/` directory, records each image's source and license metadata,
and processes the first image through the normal detection, classification,
counting, evidence, and SQLite path. No test image is committed to this
repository.

Run an attributed public-domain video through the streaming, tracking,
counting, SQLite, and annotated-output path:

```bash
./startup.sh --backend omdet_turbo --demo-video --no-display
```

The video is downloaded into the ignored `media/demo-video/` directory. Its
source, creator, Public Domain Mark, and checksums are recorded in
`media/demo-video/manifest.json`. It is functional test media, not a labelled
accuracy dataset.

Choose an input explicitly when needed:

```bash
# Attached camera
./startup.sh --source 0

# Image
./startup.sh --source ./media/litter.jpg

# Downloaded video
./startup.sh --source ./media/route.mp4

# Live stream; keep credentials outside the repository
export LITTER_STREAM_URL="rtsp://camera-host/live"
./startup.sh --source "$LITTER_STREAM_URL" --no-display

# Vehicle and route context
./startup.sh \
  --source 0 \
  --edge-device-id edge-truck-01 \
  --vehicle-id truck-12 \
  --route-id route-a
```

Press `q` in the display window or `Ctrl+C` in the terminal to stop a live run.
Run `./startup.sh --help` for all options.

## Browser operations dashboard

Start the local dashboard and API together:

```bash
./startup.sh --dashboard --backend omdet_turbo --device auto
```

Then open `http://127.0.0.1:8088`. The dashboard provides:

- camera, local video, HTTP video, and RTSP source control;
- an annotated near-real-time perception feed;
- current visible counts and unique tracked counts;
- edge-device, vehicle, and route context;
- automatic SQLite persistence for dashboard stream sessions;
- recent runs, aggregate observed counts, collection confirmations, and the
  human review queue; and
- a separate single-image inspection tool.

Prepare the reusable demonstration and dashboard in one command:

```bash
./startup.sh \
  --dashboard \
  --demo-video \
  --backend omdet_turbo \
  --device auto
```

In the dashboard, select **Use public demo video**, then start detection.
The API binds to localhost by default. Use an authenticated reverse proxy or an
SSH tunnel for a remote edge device; do not expose the unauthenticated port
directly to the internet.

## Outputs

| Output | Default location | Purpose |
|---|---|---|
| SQLite database | `state/litter-edge.db` | Durable runs, counts, review queue, confirmed collections, and integration outbox |
| Frame events | `reports/generated/run-*.jsonl` | One structured evidence record per processed frame |
| Run summary | `reports/generated/run-*-summary.json` | Throughput, source, model, device, and aggregate counts |
| Annotated media | `reports/generated/run-*-annotated.*` | Boxes, classes, confidence, track IDs, and review status |

The system reports two different count types:

- `visible_counts`: objects visible in the current frame;
- `unique_session_counts`: confirmed track IDs counted once during the run.

An object visible in 100 consecutive frames is normally counted once, not 100
times. Re-entry, long occlusion, scene cuts, and severe camera motion can still
create duplicate tracks. See [counting semantics](docs/COUNTING.md).

## Persistent counts and human review

SQLite is enabled by default and needs no database server:

```bash
python query_counts.py summary
python query_counts.py summary --vehicle-id truck-12 --route-id route-a
python query_counts.py runs --limit 20
python query_counts.py reviews --status pending
python query_counts.py outbox
```

The database deliberately separates:

- observed litter from model detections and tracks;
- human-reviewed or corrected classifications; and
- material independently confirmed as physically collected.

A detection never becomes a collection claim automatically.

Full per-detection rows are disabled by default to control disk use. Enable
them with:

```bash
./startup.sh --persist-detections
```

## HTTP API

Start the dashboard, image detection, stream control, and operational APIs:

```bash
./startup.sh --api
```

Or start only the count, review, collection, and integration APIs:

```bash
./startup.sh --counts-api
```

Examples:

```bash
curl http://127.0.0.1:8088/healthz
curl http://127.0.0.1:8088/readyz

curl \
  -H "Content-Type: image/jpeg" \
  --data-binary @media/litter.jpg \
  http://127.0.0.1:8088/v1/detect

curl "http://127.0.0.1:8088/v1/counts/summary?vehicle_id=truck-12"
curl "http://127.0.0.1:8088/v1/review-queue?status=pending"
curl "http://127.0.0.1:8088/v1/integration/events"

curl \
  -H "Content-Type: application/json" \
  -d '{"source":"0","edge_device_id":"edge-truck-01"}' \
  http://127.0.0.1:8088/v1/streams
```

Live stream sessions use the same tracker, counts, separation policy, review
queue, SQLite schema, and integration outbox as the command-line runtime. Only
one live stream is accepted by default to protect constrained edge devices.
Set `LITTER_MAX_STREAMS` deliberately if the hardware has been validated for
more.

The API binds to localhost and has no built-in authentication. Put it behind
an authenticated gateway before exposing it to a network.

## Cleanup-truck and sorting integration

```text
camera / stream
       |
       v
public or custom detector
       |
       v
standard detections -> tracking -> visible + unique counts
       |                              |
       |                              +-> SQLite / API / fleet outbox
       v
operator review and separation guidance
       |
       +-> candidate event -> planner -> safety PLC -> collection arm
                                      |
                         pickup confirmation -> SQLite / API
```

This repository is a perception and evidence component, not a safety-rated
motion controller. It must not directly energize or move a hydraulic,
pneumatic, or electric arm. Emergency stops, exclusion zones, proximity
sensing, interlocks, motion limits, and final actuation authority belong to the
truck's safety controller. See [truck integration](docs/TRUCK_INTEGRATION.md).

## Model release path

The repository implements one litter use case, not a model leaderboard.

### Current functional bootstrap

```bash
./startup.sh --backend grounding_dino
```

- model: `IDEA-Research/grounding-dino-tiny`;
- automatic public download through Hugging Face Transformers;
- configurable text-prompt categories;
- no API key;
- no user training prerequisite;
- portable PyTorch reference path for CPU, NVIDIA CUDA, and AMD ROCm.

Open-vocabulary support makes the catalog configurable; it does not guarantee
equal accuracy for every prompt, scene, object size, city, camera, or weather
condition. Deployment accuracy and sustained frame rate must be measured on
representative data and the intended device. The bootstrap exists so anyone can
exercise the full source, tracking, counting, SQLite, review, and API workflow
while the release checkpoint is pending.

### No-training visual-model screen

```bash
./startup.sh --backend omdet_turbo --source 0
```

- model: `omlab/omdet-turbo-swin-tiny-hf`;
- Apache-2.0 model card and checkpoint;
- approximately 0.1B parameters;
- confidence-scored open-vocabulary boxes;
- automatic download through Transformers;
- PyTorch reference path for CPU, NVIDIA CUDA, Apple MPS, and AMD ROCm.

This backend is operationally integrated but is not yet the validated release
model. Its purpose is to determine whether a public no-training visual detector
can satisfy the litter use case before central fine-tuning is undertaken.

### Selected deployable release

The project release will use one litter-specific RF-DETR Nano checkpoint:

```bash
./startup.sh --backend rfdetr --source 0
```

That command already supports checksum-verified automatic download through
[`config/model-release.json`](config/model-release.json). It becomes the normal
release path only after a checkpoint has complete class coverage, held-out
accuracy evidence, count evidence, and edge-device acceptance results. Until
then, the manifest intentionally remains `pending`.

## Edge-device portability

| Target | Reference path | Current status |
|---|---|---|
| CPU | PyTorch + Transformers | Implemented; performance depends on host |
| NVIDIA CUDA | PyTorch CUDA | Implemented; device validation required |
| AMD ROCm / Strix Halo | PyTorch ROCm (`cuda` device API) | Code path implemented; device validation required |
| Jetson Orin 8 GB | JetPack-compatible PyTorch or optimized platform service | Integration documented; no changes made to the shared device |
| ONNX/OpenVINO/TensorRT | Target-specific exported adapter | Optional future optimization |

On an accelerator target, install the vendor-supported PyTorch build first and
set `LITTER_PYTHON` to that environment. The launcher refuses to create a
generic first-time PyTorch environment on Jetson because it could replace or
conflict with the JetPack-compatible stack.

No software was installed and no configuration was changed on the currently
shared Jetson during development of this repository.

## Container

The included container is a CPU/reference API deployment:

```bash
docker compose build
docker compose up
```

The bootstrap model is downloaded into the container user's model cache on first
detection unless a cache volume is added by the deployer. Use a
vendor-supported base image for NVIDIA, AMD, or Jetson acceleration.

## Evaluation

Evaluation checks whether this solution meets the use case; it does not compare
model families.

Detection/classification metrics can include precision, recall, F1, mAP, and
per-class results. Counting evaluation reports visible-count and
unique-session-count error:

```bash
python evaluate_counts.py \
  --events reports/generated/route.jsonl \
  --ground-truth data/count-ground-truth.json \
  --output reports/generated/count-accuracy.json
```

The public repository does not claim a particular accuracy, frame rate, memory
use, or power result until measurements are produced from representative data
on the target deployment.

## Maintainer model-release workflow

Training is not part of deployment. Project maintainers use the following
workflow to build the one published litter checkpoint:

```bash
python -m pip install -e ".[runtime,train]"
python prepare_training_data.py
python train.py --model rfdetr-nano --data data/taco-operational-v1
```

The data command downloads public TACO media, retains attribution and checksums,
maps its fine-grained labels to the operational taxonomy, and creates grouped
COCO train/validation/test splits. It also reports classes with no examples.
TACO is bootstrap data; representative truck, roadside, motion, weather, and
camera data must be added before a model release.

## Software and MSc thesis

The reusable application and the academic evaluation are separate:

- the repository provides deployable source code, configuration, schemas,
  tests, persistence, APIs, and integration guidance;
- the MSc thesis evaluates the single versioned release configuration on
  representative data and edge hardware.

The thesis does not compare model families. It evaluates whether the selected
release implementation meets the use case. It is not a prerequisite for cloning
or using the application. See
[software and research separation](docs/SOFTWARE_AND_RESEARCH.md).

## Repository layout

```text
src/litter_edge/     runtime, adapters, tracking, counting, storage, and API
config/              prompts, class catalog, separation policy, and settings
schemas/             stable event contracts
deploy/              CPU, NVIDIA, AMD, Jetson, and service examples
docs/                operations, architecture, integration, and research docs
tests/               dependency-light automated tests
thesis/              prospective MSc manuscript
```

Runtime directories such as `models/`, `runs/`, and `reports/generated/` are
created when needed. Empty placeholder `.gitkeep` files are intentionally not
published.

## Validation

```bash
make validate
```

`make validate` is the fast dependency-light code test. The real model and
download path require internet access and are intentionally explicit:

```bash
./startup.sh --demo --no-display
python query_counts.py summary
```

Successful completion creates annotated evidence under `reports/generated/`
and a persisted run in `state/litter-edge.db`.

## Security, privacy, and licensing

The project detects litter, not people. Face identification, person
re-identification, license-plate recognition, behavior scoring, and automated
enforcement are out of scope.

Do not commit stream credentials, private imagery, datasets, model weights, or
raw device inventories.

Original project code and software documentation are Apache-2.0. Public model
weights, datasets, exported artifacts, and academic material can have separate
terms. Review [LICENSE-NOTICE.md](LICENSE-NOTICE.md) before redistribution.

Citation metadata is in [CITATION.cff](CITATION.cff).
