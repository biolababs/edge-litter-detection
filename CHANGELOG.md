# Changelog

## 0.8.0 - 2026-10-21

- Added `./startup.sh --demo` for an automated real-model functional test.
- Added a bounded TACO sample downloader that retains per-image source,
  checksum, category, and license metadata in a local manifest.
- Kept downloaded test images and their generated manifest outside Git.
- Added unit and launcher tests for demo-data preparation and execution.
- Added Python 3.13–3.14 support with NumPy 2.x while retaining NumPy 1.26 for
  Python 3.10–3.12 and Jetson-compatible environments.
- Made non-graphical Linux and `--no-display` startup use headless OpenCV.

## 0.7.0 - 2026-10-21

- Made public Grounding DINO Tiny the automatically downloaded default model.
- Removed custom training and a private checkpoint as prerequisites for normal
  use.
- Expanded the default operational catalog from five fixed classes to 16
  configurable open-vocabulary litter prompts.
- Retained RF-DETR training and checkpoints as an optional advanced profile.
- Updated the launcher, API, container, deployment profiles, tests, and
  documentation for the public-model workflow.
- Removed unnecessary `.gitkeep` placeholder files; runtime directories are
  created when needed.

## 0.6.0 - 2026-10-21

- Added default offline SQLite persistence for runs, frame counts, class
  totals, optional detection rows, and externally confirmed collections.
- Added truck, route, and edge-device identifiers throughout events and
  summaries.
- Added configurable separation guidance and a human review queue for uncertain
  classifications.
- Added durable integration outbox events for confirmed objects, reviews,
  run completion, and collection confirmation.
- Added count, run, review, collection, and integration API workflows.

## 0.5.0 - 2026-10-20

- Replaced the manual-first README with a professional standalone software
  quick start.
- Added `startup.sh` to automate environment setup, model verification, source
  discovery, inference, output naming, and API startup.
- Added local camera and media/stream probing without loading the model.
- Added checksum-verified HTTPS model installation.
- Added explicit software-versus-thesis and input-source documentation.

## 0.4.0 - 2026-10-20

- Made the reusable application hardware-neutral while keeping Jetson as a
  thesis evaluation target.
- Added RF-DETR as the single implementation model; model comparison is out of
  scope.
- Added class-stabilized tracking, visible counts, and unique-session counts.
- Added held-out RF-DETR accuracy and aggregate count-accuracy commands.
- Added image/video/camera/stream execution, JSONL evidence, annotated output,
  and a single-image HTTP API.
- Added a CPU reference container plus NVIDIA CUDA and AMD ROCm deployment
  profiles.
- Published the initial `biolababs/edge-litter-detection` source repository.

## 0.3.0 - 2026-10-20

- Recorded the confirmed Jetson Orin Nano 8 GB Super and JetPack 6.2.3 target.
- Added a sanitized read-only inventory report and shared-workload constraints.
- Added conservative detector memory gates and a recorded-video-first test plan.
- Deferred any additional continuous VLM because the target already hosts LLM
  services.
- Updated the thesis and publication checklist without claiming model results.

