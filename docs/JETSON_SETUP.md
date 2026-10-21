# Jetson Orin Nano 8 GB Super deployment plan

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

## Installation rule

No installation is currently authorized.

In a later approved test window, prefer an isolated JetPack-compatible
container or dedicated environment. Do not modify the system Python used by the
existing project. Any PyTorch build must match the installed JetPack/CUDA stack;
a generic wheel is not assumed to provide working Jetson GPU support.

Preferred options:

1. A version-pinned NVIDIA-compatible container with explicit memory and port
   limits.
2. A dedicated environment using NVIDIA-compatible framework builds, only if a
   container cannot support the public Grounding DINO runtime.

The commands below are a future procedure, not authorization to execute them:

Then:

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

## Public-model runtime validation

Start with a recorded-video smoke test because no camera was connected at
inventory time:

```bash
LITTER_PYTHON="$PWD/.venv/bin/python" \
  ./startup.sh --skip-install \
  --backend grounding_dino \
  --source sample.mp4 \
  --device cuda \
  --no-display
```

The first authorized run downloads and caches
`IDEA-Research/grounding-dino-tiny` unless the model cache is populated in the
isolated environment beforehand. Measure the reference runtime before deciding
whether an optimized NVIDIA platform service or exported artifact is required.

Any optimized path must preserve the configured prompt/output contract and be
re-evaluated on the same held-out data. INT8 is deferred until representative
calibration data and a validated runtime path exist.

## Official references

- NVIDIA JetPack: https://developer.nvidia.com/embedded/jetpack
- NVIDIA Jetson Orin Nano series:
  https://www.nvidia.com/en-us/autonomous-machines/embedded-systems/jetson-orin/nano-super-developer-kit/
- Transformers Grounding DINO:
  https://huggingface.co/docs/transformers/model_doc/grounding-dino

