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

## Current validation evidence

The application and OmDet-Turbo path were functionally exercised on an AWS
`g4dn.xlarge` with a Tesla T4. A repeated-image, model-only benchmark reported:

- 16.53 frames per second;
- 58.98 ms mean inference latency and 61.03 ms p95 latency; and
- 0.55 GiB peak allocated accelerator memory.

This is useful implementation evidence, but it is not a sustained camera,
full-pipeline, Jetson, AMD, thermal, or power benchmark.

## Platform status

| Platform | Status |
|---|---|
| CPU | Functional reference path |
| NVIDIA CUDA | Functional path; Tesla T4 smoke and model benchmark completed |
| NVIDIA Jetson Orin 8 GB | Deployment path documented; target validation pending |
| AMD ROCm / Ryzen AI Max / Strix Halo | PyTorch path implemented; target validation pending |
| Apple silicon | MPS development path available; target validation pending |

The shared Jetson device was not modified during repository development.

## Capacity planning

Disk use grows from four sources:

- Python and accelerator runtime packages;
- downloaded model checkpoints;
- annotated output media;
- SQLite observations and optional per-detection rows.

Counts-only storage is compact. Annotated video and
`--persist-detections` should have an explicit retention policy on vehicles and
long-running sorting lines.

