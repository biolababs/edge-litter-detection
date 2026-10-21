# Changelog

## Unreleased

- Fixed OmDet-Turbo loading on JetPack-compatible PyTorch when Swin
  non-persistent attention buffers remain on the meta device.
- Constrained Transformers to the PyTorch-2.4-compatible 4.x series and fixed
  CUDA memory measurement on JetPack versions that require an indexed device.
- Added measured Jetson Orin Nano 8 GB coexistence evidence for a 50-sample
  detector benchmark, 3,622-frame full-file stability workflow, SQLite persistence,
  annotated output, dashboard stream control, counts API, thermals, and
  whole-board power.
- Documented that the current public-model Jetson path is functional at 5.54
  detector FPS and 4.94 full-pipeline FPS but does not meet the provisional
  15 FPS target.
- Reworked the GitHub landing page around outcomes, five-minute setup, input
  sources, durable outputs, architecture, deployment, and minimum/recommended
  hardware tiers.
- Added hardware requirements, a documentation index, support policy, code of
  conduct, issue forms, pull-request guidance, Dependabot, dependency review,
  and CodeQL.
- Changed the unauthenticated API and Compose defaults to private-by-default
  loopback exposure and documented SSH-tunnel and authenticated-gateway access.
- Added bounded and type-checked image uploads, request concurrency limits,
  retained-stream limits, security response headers, and stricter API payload
  validation.
- Pinned public Hugging Face models to immutable revisions, required
  SafeTensors, disabled remote model code, and upgraded Pillow to 13 on Python
  3.11 and later.
- Replaced SHA-1 demo verification with SHA-256, removed dynamic SQL assembly,
  made JSON output atomic, and added API security regression tests.
- Added a complete optional custom-data training guide covering class
  contracts, COCO layout, representative collection, leakage-resistant splits,
  smoke training, held-out evaluation, runtime testing, and checkpoint release.
- Clarified that the public backends work out of the box while maintainers and
  advanced site teams can fine-tune for deployment-specific accuracy.

## 0.10.1 - 2026-10-21

- Replaced the road-driving functional demo with an attributed,
  checksum-verified material-recovery-facility video showing mixed recyclables,
  conveyor flow, manual separation, and baled material.
- Added WebM integrity validation and documented the demo's separate CC BY-SA
  3.0 license and Wikimedia permission confirmation.
- Updated the browser dashboard to select the sorting-floor demonstration.

## 0.10.0 - 2026-10-21

- Added a responsive browser operations dashboard served by the existing API.
- Added server-side camera, video, HTTP, and RTSP session control with
  annotated frame polling, tracking, counting, review routing, and SQLite
  persistence.
- Limited live dashboard concurrency to one stream by default for predictable
  edge-device resource use.
- Added an attributed, checksum-verified public-domain video downloader for
  reproducible functional stream testing without committing media to Git.
- Added `./startup.sh --dashboard` and `--demo-video` automated workflows.
- Added regression tests for stream persistence, credential redaction, video
  integrity, attribution, and launcher behavior.

## 0.9.1 - 2026-10-21

- Fixed backend overrides in the benchmark, direct inference CLI, and API so
  OmDet-Turbo automatically loads its own checkpoint instead of the configured
  Grounding DINO bootstrap checkpoint.
- Added regression coverage for backend-aware model selection and preserved
  explicit custom-model overrides.

## 0.9.0 - 2026-10-21

- Selected one project-maintained RF-DETR Nano checkpoint as the release
  detector while retaining Grounding DINO Tiny as a functional bootstrap.
- Added automated, attributed TACO-to-operational COCO dataset preparation with
  deterministic source-group train, validation, and held-out test splits.
- Added conservative category mapping, per-image licenses and checksums,
  download-failure evidence, and explicit missing-class release blockers.
- Added training-time validation that COCO class IDs and names exactly match
  the runtime taxonomy.
- Added repeatable static-image benchmarking and direct PyTorch accelerator
  allocation, reservation, free-memory, and peak-memory evidence.
- Added an Apache-2.0 OmDet-Turbo Tiny open-vocabulary backend for a
  confidence-scored, no-training acceptance screen on the same TACO data.
- Updated the reusable software and MSc plan around one evaluated use case:
  maintainers publish weights; deployment users do not train.

## 0.8.1 - 2026-10-21

- Fixed current Transformers Grounding DINO output handling by preferring
  stable numeric label IDs over ambiguous decoded text spans.
- Supplied the configured class labels to post-processing for current
  Transformers compatibility.
- Routed genuinely unresolved labels to `other_litter` for human review instead
  of terminating an operational run.
- Added the composite-label failure observed during the CUDA smoke test as a
  regression test.

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

