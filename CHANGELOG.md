# Changelog

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

