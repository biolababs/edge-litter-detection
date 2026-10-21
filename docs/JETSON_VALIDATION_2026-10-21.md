# Jetson Orin Nano coexistence validation — 21 October 2026

## Outcome

The public OmDet-Turbo workflow ran successfully on the intended 8 GB Jetson
while the device's existing services remained active. Image benchmarking,
recorded-video detection, tracking, counting, SQLite persistence, annotated
media, the browser dashboard, and the counts API all completed.

The current eager PyTorch path is functional but does not meet the provisional
15 FPS target. It measured 5.54 FPS for the repeated-image detector benchmark
and 4.94 FPS across the complete 3,622-frame video workflow. This is suitable
for low-rate inspection and workflow integration testing; higher-rate vehicle
or sorting-line operation requires optimization and another acceptance run.

No accuracy or count-error claim is made. The demonstration media has no
ground truth for the project's 16-class operational taxonomy.

## Device and isolation

| Item | Validated condition |
|---|---|
| Device | NVIDIA Jetson Orin Nano Engineering Reference Developer Kit Super |
| Memory | 7.4 GiB physical/unified memory |
| Host software | Ubuntu 22.04.5, JetPack 6.2.3, L4T 36.5.2 |
| Power mode | MAXN_SUPER |
| Camera | None attached; recorded media used |
| Co-resident workload | Existing local AI and application services remained active |
| System changes | No system package, system Python, service, clock, or power-mode change |
| Test isolation | Dedicated `/data/edge-litter-validation` tree and constrained containers |
| Container limit | 4 GiB memory, no additional container swap, 512 PIDs |
| Network exposure | Dashboard test published only on Jetson loopback |

The validated software revision was
`756fa2ae0b8686bb4b97940911710dc73f8efd90`.

The test used the pinned community image:

```text
dustynv/l4t-pytorch@sha256:a05c85def9139c21014546451d3baab44052d7cabe854d937f163390bfd5201b
```

It supplied Python 3.10.12, PyTorch 2.4.0, torchvision
0.19.0a0+48b1edf, CUDA access, and TensorRT 10.4.0. Transformers was constrained
to the compatible 4.x series and measured at 4.57.6. The image is not an
NVIDIA-supported production base image; production deployment should use a
reviewed vendor-supported image or explicitly approve this supply-chain
choice.

## Repeated-image detector benchmark

Protocol: OmDet-Turbo Tiny, CUDA automatic mixed precision, 640-pixel model
input, 10 warm-up calls, and 50 measured repetitions of one attributed TACO
image.

| Measure | Result |
|---|---:|
| Throughput | 5.54 FPS |
| Mean detector latency | 174.30 ms |
| Median detector latency | 173.04 ms |
| p95 detector latency | 175.65 ms |
| Maximum detector latency | 213.34 ms |
| Peak accelerator allocation | 0.70 GiB |
| Peak accelerator reservation | 0.74 GiB |
| Maximum process RSS | 2.20 GiB |
| Observed system-available-memory reduction | 0.95 GiB |
| Minimum system-available memory | 2.54 GiB |
| Peak GPU temperature | 55.16 °C |
| Mean board input power during capture | 8.33 W |
| Peak board input power during capture | 16.62 W |

The host had 155 MiB of pre-existing swap use before the benchmark and 158 MiB
afterward. The subsequent video run did not increase swap. Board input power is
whole-device power, including co-resident services, and is not detector-only
power.

## Initial video smoke

The normal launcher downloaded and checksum-verified the attributed Wikimedia
recycling-facility video, then processed 120 frames:

```bash
./startup.sh \
  --skip-install \
  --demo-video \
  --backend omdet_turbo \
  --device cuda \
  --no-display \
  --max-frames 120 \
  --edge-device-id jetson-orin-nano-01 \
  --vehicle-id validation \
  --route-id video-smoke
```

| Measure | Result |
|---|---:|
| Frames | 120 |
| Wall time | 25.94 s |
| Source-to-result throughput | 4.63 FPS |
| Mean detector-call latency | 192.80 ms |
| Peak Jetson RAM used | 4,845 MB |
| Peak GPU temperature | 57.13 °C |
| Mean board input power during capture | 10.51 W |
| Peak board input power during capture | 14.69 W |
| Swap change | 0 MiB |

The run completed without interruption and produced:

- a 6.9 MiB annotated MP4;
- a 239 KiB per-frame JSONL record;
- a JSON run summary;
- tracked visible and unique-session counts; and
- a 196 KiB SQLite database containing the completed run.

The reported class counts are not accuracy results. Visual inspection showed
that some public-model predictions on the demonstration media require human
review, which is consistent with the application's review-first design.

## Full-file stability run

The same pinned software and constrained container then processed all 3,622
frames of the 120.85-second source file:

| Measure | Result |
|---|---:|
| Frames | 3,622 |
| Continuous processing time | 733.54 s |
| Source-to-result throughput | 4.94 FPS |
| Mean detector-call latency | 178.60 ms |
| Maximum application-container memory | approximately 1.97 GiB at observed checkpoints |
| Peak total Jetson RAM used | 4,851 MB |
| Mean GPU temperature during telemetry | 63.86 °C |
| Peak GPU temperature | 66.31 °C |
| Mean board input power during telemetry | 14.53 W |
| Peak board input power | 15.81 W |
| Swap | 158 MiB before; 147 MiB after |

Memory and temperature reached a stable range rather than increasing
continuously. The run completed without interruption and finalized a 215 MiB
annotated MP4, an 8.4 MiB JSONL record, a JSON summary, and a 3.6 MiB SQLite
database. This is a bounded full-file stability result, not a multi-hour or
production endurance qualification.

## Dashboard and API

A loopback-only dashboard service was started in a constrained container. The
following checks passed:

- dashboard `GET /` returned HTTP 200;
- CSP, frame denial, no-sniff, and restrictive permissions headers were
  present;
- `POST /v1/streams` started a CUDA video session;
- the session completed 30 frames and served a 960×540 annotated JPEG;
- `/v1/counts/summary` returned persisted route/device counts; and
- `/v1/runs` returned the completed SQLite run.

The 30-frame dashboard stream measured 1.77 source-to-result FPS because the
timer included lazy model loading. It is a functional UI/API measurement, not
the steady-state performance result.

## Interpretation

| Gate | Status |
|---|---|
| Public-model loading and CUDA inference | Pass |
| Detection, classification, tracking, and unique-session counting | Functional pass |
| JSONL, summary, annotated media, and SQLite persistence | Pass |
| Dashboard, annotated frame, counts API, and security headers | Pass |
| At least 2 GiB system-available memory during benchmark | Pass |
| Provisional 15 FPS target | Not met |
| Target-domain accuracy | Not evaluated |
| Video count error | Not evaluated |
| Bounded 3,622-frame full-file stability | Pass |
| Repeated and multi-hour endurance/throttling acceptance | Not evaluated |
| Production readiness | Not established |

Next engineering work should focus on a reviewed Jetson production base image,
TensorRT or another validated optimized adapter, bounded frame sampling for
high-rate sources, and repeated/multi-hour measurements. Accuracy work remains
separate and requires representative labeled images plus track-annotated
video.

## Evidence

Machine-readable results and raw `tegrastats` captures are stored under
`paper/evidence/`. Their checksums and limitations are recorded in
`paper/evidence/jetson_orin_nano_validation.json`.
