# Jetson read-only inventory — 20 October 2026

## Scope and safety

This inventory was captured from the private target device using an
unprivileged account and the repository's read-only inventory script. It did
not install packages, write files, start or stop services, change
configuration, create containers, or run an inference workload.

The device is already used by another project. No deployment or benchmark is
authorized until a separate maintenance/test window is approved.

## Confirmed platform

| Item | Observed value |
|---|---|
| Product | NVIDIA Jetson Orin Nano Engineering Reference Developer Kit Super |
| Board compatibility | `p3768-0000+p3767-0005-super`, `p3767-0005`, `tegra234` |
| Architecture / CPU | aarch64; 6 Cortex-A78AE cores; up to 1728 MHz |
| Operating system | Ubuntu 22.04.5 LTS |
| Kernel | 5.15.199-tegra |
| JetPack | 6.2.3 |
| L4T | 36.5.2 |
| Power mode | MAXN_SUPER |
| Python | 3.10.12 |
| TensorRT Python package | 10.3.0 |
| OpenCV | 4.5.4; CUDA-enabled device count reported as 0 |

The `jetson_clocks --show` command requires root, so clock-lock status was not
collected. No privileged command was attempted.

## Resource snapshot

| Resource | Observed value |
|---|---|
| Physical memory | 7.4 GiB total; 2.5 GiB used; 4.5 GiB available |
| Swap | 19 GiB total; unused at capture time |
| Root storage | NVMe; 915 GiB filesystem; 772 GiB available |
| Data storage | 231.4 GiB eMMC/SD partition mounted at `/data` |
| Load average | 0.19, 0.16, 0.15 |
| CPU temperature | approximately 49.2 °C |
| GPU temperature | approximately 50.1 °C |
| Junction temperature | approximately 50.0 °C |
| Camera devices | no `/dev/video*` device observed |

Swap is not counted as safe model capacity for real-time inference. A model
that depends on swapping will fail the deployment gate.

## Runtime availability

Present:

- TensorRT 10.3.0 Python package;
- Docker;
- `tegrastats`;
- NVIDIA L4T CUDA and multimedia packages.

Not observed in the current system Python or command path:

- PyTorch;
- RF-DETR;
- `nvcc`;
- `trtexec`;
- a CUDA-enabled OpenCV device.

The absence of these tools is not a request to install them. A later,
explicitly authorized deployment should use an isolated, JetPack-compatible
container or dedicated environment and must not alter the existing project's
system Python.

## Existing workload and network reservations

The snapshot showed active local LLM inference, application, and development
services. No running Docker containers were visible to the inventory user.
Multiple ports were already reserved. A deployment must rediscover and avoid
active listeners rather than relying on a published port list.

## Design consequences

1. Validate the public Grounding DINO Tiny profile first; perform optional
   custom training off-device only if later measurements justify it.
2. Do not add a continuous VLM or second LLM to the initial real-time path.
3. Prefer a detector process using no more than 1.5 GiB of incremental memory.
4. Reject a deployment above 2.0 GiB incremental memory or one that
   leaves less than 2.0 GiB available to the existing workload.
5. Begin later smoke tests with recorded video because no camera was present.
6. Run coexistence benchmarks without stopping existing services, unless the
   device owner separately approves a controlled exclusive benchmark.
7. Label coexistence and exclusive measurements as different experiment
   conditions.
8. Avoid the currently occupied ports and do not assume Docker is available
   for exclusive use.

## Implementation

At the time of this inventory, RF-DETR Nano was the planned implementation.
Version 0.7.0 superseded that plan with public Grounding DINO Tiny as the
no-training default and retained RF-DETR only as an optional custom profile.
The hardware observations remain valid historical evidence. Target validation
checks detection/classification accuracy, counting accuracy, full-pipeline
latency, sustained FPS, incremental memory, power, thermal stability,
operational reliability, and licensing. It does not compare model families.

## Evidence handling

The full raw output is stored locally at
`reports/generated/jetson_inventory.txt`. That directory is excluded from Git
so transient process and network details are not accidentally published. This
document is the sanitized, publication-oriented summary.
