# Hardware requirements

This project has two hardware tiers: a minimum functional baseline and a
recommended real-time evaluation target. The minimum can run the workflow; it
does not guarantee a production frame rate.

## Minimum functional baseline

| Component | Minimum |
|---|---|
| Architecture | 64-bit x86_64 or ARM64 |
| CPU | 4 logical cores |
| Memory | 8 GiB RAM or unified memory |
| Storage | 10 GiB free for the environment, model cache, and outputs |
| Python | 3.10–3.14 |
| Operating system | Linux recommended; macOS is supported for development |
| Accelerator | Optional |
| Camera | Optional UVC camera, local image/video, HTTP video, or RTSP source |
| Network | Required for the initial dependency and model download |

A CPU-only machine is suitable for installation checks, API integration, test
images, and low-rate processing. Throughput depends strongly on image size,
scene complexity, processor generation, and selected backend.

## Recommended real-time evaluation target

| Component | Recommended starting point |
|---|---|
| CPU | 6 or more modern logical cores |
| Host memory | 16 GiB for a discrete-GPU system |
| Accelerator memory | 8 GiB or more |
| Storage | 20 GiB free, preferably SSD |
| Camera | 720p or 1080p UVC/RTSP stream |
| Runtime | Vendor-supported CUDA, ROCm, or JetPack PyTorch environment |

An 8 GiB accelerator is a planning baseline, not a statement that every
backend, resolution, or stream rate will satisfy real-time requirements.
Validate sustained throughput, memory, thermals, power, accuracy, and count
error on the intended device and representative footage.

The maintained public-model dependency line requires PyTorch 2.6 or newer,
torchvision 0.21 or newer, and Transformers 5.20 or newer. Jetson deployments
must use builds compatible with the installed JetPack release; the installer
must not replace the device's system framework or CUDA packages.

## Current validation evidence

The application and OmDet-Turbo path were functionally exercised on an AWS
`g4dn.xlarge` with a Tesla T4. A repeated-image, model-only benchmark reported:

- 16.53 frames per second;
- 58.98 ms mean inference latency and 61.03 ms p95 latency; and
- 0.55 GiB peak allocated accelerator memory.

This is useful implementation evidence, but it is not a sustained camera,
full-pipeline, Jetson, AMD, thermal, or power benchmark.

An authorized coexistence validation then exercised the intended Jetson Orin
Nano 8 GB while its existing services remained active. With OmDet-Turbo Tiny,
PyTorch 2.4.0, automatic mixed precision, and a constrained container:

- the 50-sample repeated-image benchmark measured 5.54 FPS, 174.30 ms mean
  detector latency, and 175.65 ms p95 latency;
- peak accelerator allocation was 0.70 GiB, maximum process RSS was 2.20 GiB,
  and at least 2.54 GiB system memory remained available;
- a complete 3,622-frame video run measured 4.94 source-to-result FPS and
  178.60 ms mean detector-call latency over 733.54 seconds;
- the full-file run reached 66.31 °C maximum GPU temperature and 15.81 W
  maximum whole-board input power, while swap decreased from 158 MiB to
  147 MiB;
  and
- annotated MP4, JSONL, summary, SQLite, dashboard, annotated-frame, and counts
  API paths completed successfully.

The measured public-model path is functional for low-rate operation but did
not meet the provisional 15 FPS target.

A subsequent secured-runtime profile used PyTorch 2.7.0, torchvision 0.22.0,
Transformers 5.20.2, and three 300-frame repetitions after 10 warm-up calls:

- mean source-to-result throughput was 5.1877 FPS with 0.0104 FPS population
  standard deviation;
- model forward averaged 71.10% of wall time, preprocessing 13.69%, and
  annotation/output 10.59%;
- tracking, JSONL, and SQLite together averaged 0.91% of wall time;
- minimum system-available memory was 2,280 MiB, peak GPU temperature was
  63.94 °C, and peak whole-board input power was 15.10 W; and
- all three runs emitted identical counts on the fixed video.

These are short engineering results on unlabelled demonstration media, not
target-domain accuracy, count-error, multi-hour endurance, or
production-readiness evidence.

## Platform status

| Platform | Status |
|---|---|
| CPU | Functional reference path |
| NVIDIA CUDA | Functional path; Tesla T4 smoke and model benchmark completed |
| NVIDIA Jetson Orin 8 GB | Full workflow and dashboard verified; preliminary coexistence performance measured |
| AMD ROCm / Ryzen AI Max / Strix Halo | PyTorch path implemented; target validation pending |
| Apple silicon | MPS path exercised on the 212-image public-data evaluation |

See `JETSON_VALIDATION_2026-10-21.md` for the exact runtime, isolation,
telemetry, acceptance interpretation, and evidence checksums.

## Capacity planning

Disk use grows from four sources:

- Python and accelerator runtime packages;
- downloaded model checkpoints;
- annotated output media;
- SQLite observations and optional per-detection rows.

Counts-only storage is compact. Annotated video and
`--persist-detections` should have an explicit retention policy on vehicles and
long-running sorting lines.

