# Jetson Orin Nano 8 GB Super deployment and validation

## Confirmed hardware

A read-only inventory on 20 October 2026 confirmed:

- NVIDIA Jetson Orin Nano Engineering Reference Developer Kit Super;
- JetPack 6.2.3 and L4T 36.5.2 on Ubuntu 22.04.5;
- MAXN_SUPER power mode;
- 7.4 GiB physical memory, with 4.5 GiB available in the captured snapshot;
- TensorRT 10.3.0 for Python;
- no PyTorch or project detector runtime in the system Python;
- active local LLM, application, and development services;
- no camera device present.

See `JETSON_INVENTORY_2026-10-20.md` for the sanitized inventory.

## Software baseline

Keep JetPack 6.2.3/L4T 36.5.2 fixed for this experiment series. Do not upgrade,
install a framework, or otherwise change the shared device merely to prepare
this project. The current state is the deployment target unless the device
owner separately approves a maintenance change.

Record:

```bash
cat /etc/nv_tegra_release
uname -a
python3 --version
dpkg-query -W nvidia-jetpack
```

Run the repository health check:

```bash
python scripts/jetson_healthcheck.py \
  --output reports/generated/jetson_environment.json
```

## Validated installation rule

The authorized validation used an isolated JetPack-compatible container and
did not modify the system Python, system packages, existing services, power
mode, or clock configuration. Any PyTorch build must match the installed
JetPack/CUDA stack; a generic wheel is not assumed to provide working Jetson
GPU support. The maintained Transformers 5.20 public-model path requires
PyTorch 2.6 or newer and torchvision 0.21 or newer.

Preferred options:

1. A digest-pinned NVIDIA-compatible container with explicit memory and port
   limits.
2. A dedicated environment using NVIDIA-compatible framework builds, only if a
   container cannot support the selected detector runtime.

The following dedicated-environment path remains an alternative and was not
used for the reported Jetson result:

```bash
python3 -m venv --system-site-packages .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements-jetson.txt
python -m pip install -e .
```

After that environment exists, the normal application entry point remains the
same:

```bash
LITTER_PYTHON="$PWD/.venv/bin/python" \
  ./startup.sh --skip-install --source sample.mp4 --no-display
```

On Jetson, `startup.sh` refuses to create a generic PyTorch environment. This
prevents an accidental installation that is incompatible with the fixed
JetPack/CUDA stack.

## Power and clocks

Record the selected power mode and keep it fixed for the validation run.

```bash
sudo nvpmodel -q
sudo jetson_clocks --show
```

The observed power mode was MAXN_SUPER. Clock-lock status was not collected
because `jetson_clocks --show` required root. Use maximum clocks only if that is
part of an approved and declared experiment condition.
Ensure active cooling and stable power. Capture `tegrastats` during every
reported performance run:

```bash
tegrastats --interval 1000 \
  --logfile reports/generated/tegrastats.log
```

Stop it after the benchmark and retain both files.

## Coexistence and memory rules

The device is shared with active LLM and application services. Initial
deployment gates are:

- preferred detector incremental memory at or below 1.5 GiB;
- hard initial detector limit of 2.0 GiB;
- at least 2.0 GiB available memory remaining for the existing workload;
- no swap-dependent operation or sustained memory growth;
- no use of ports already occupied by the device's existing services.

Do not stop or reconfigure existing services for a benchmark. If the device
owner later authorizes an exclusive benchmark, report it separately from the
normal coexistence condition.

## Public visual-model acceptance screen

Start with a recorded-video smoke test because no camera was connected at
inventory time:

```bash
LITTER_PYTHON="$PWD/.venv/bin/python" \
  ./startup.sh --skip-install \
  --backend omdet_turbo \
  --source sample.mp4 \
  --device cuda \
  --no-display
```

The first authorized run downloads and caches
`omlab/omdet-turbo-swin-tiny-hf` unless the model cache is populated in the
isolated environment beforehand. OmDet-Turbo requires the JetPack-compatible
PyTorch and torchvision packages plus `timm` and Transformers. Measure the
complete runtime before deciding whether it passes the use case.

Any optimized path must preserve the configured prompt/output contract and be
re-evaluated on the same held-out data. INT8 is deferred until representative
calibration data and a validated runtime path exist.

## Measured result

The authorized coexistence test completed on 21 October 2026. OmDet-Turbo Tiny
measured 5.54 FPS in a 50-sample repeated-image benchmark and 4.94 FPS through
the complete 3,622-frame video, tracking, annotation, JSONL, and SQLite path.
Minimum system-available memory was 2.54 GiB; the 733.54-second processing run
reached 66.31 °C and 15.81 W peak whole-board input power. Dashboard stream
control, annotated frame delivery, and counts queries also passed.

The workflow is functional, but the provisional 15 FPS target was not met.
Accuracy, count error, repeatability, multi-hour endurance, and production
readiness remain unproven.
See `JETSON_VALIDATION_2026-10-21.md` and `paper/evidence/` for the complete
protocol and machine-readable evidence.

To identify the optimization opportunity instead of timing only the detector:

```bash
./startup.sh \
  --backend omdet_turbo \
  --source /path/to/representative-video.mp4 \
  --device cuda \
  --warmup-calls 10 \
  --profile-timing \
  --no-display
```

Use the `timing_profile.components_ms` section in the generated summary.
Internal detector phases are available for OmDet-Turbo. Profiling synchronizes
CUDA around those phases and should be repeated with the same profiling
setting.

## Official references

- NVIDIA JetPack: https://developer.nvidia.com/embedded/jetpack
- NVIDIA Jetson Orin Nano series:
  https://www.nvidia.com/en-us/autonomous-machines/embedded-systems/jetson-orin/nano-super-developer-kit/
- Transformers OmDet-Turbo:
  https://huggingface.co/docs/transformers/model_doc/omdet-turbo

