# Supplementary reproducibility record

This supplement contains commands moved out of the main manuscript. It targets
Edge Litter Detection version 0.11.0. The principal warmed Jetson profile was
executed at commit:

`618954e5921305addbd147ccc96ea1d78fe34c6e`

## Clean-clone demonstration

```bash
git clone https://github.com/biolababs/edge-litter-detection.git
cd edge-litter-detection
git checkout 618954e5921305addbd147ccc96ea1d78fe34c6e
./startup.sh --backend omdet_turbo --demo-video --no-display
```

## Camera, stream, and dashboard

```bash
./startup.sh --source 0 --backend omdet_turbo

export LITTER_STREAM_URL="rtsp://camera-host/live"
./startup.sh \
  --source "$LITTER_STREAM_URL" \
  --backend omdet_turbo \
  --no-display

./startup.sh \
  --dashboard \
  --demo-video \
  --backend omdet_turbo \
  --device auto
```

Keep the service on loopback. For a remote edge device, use an authenticated
SSH tunnel or organization-managed gateway instead of exposing the API
directly to the public Internet.

## Persisted counts and review records

```bash
.venv/bin/python query_counts.py runs --limit 10
.venv/bin/python query_counts.py summary
.venv/bin/python query_counts.py reviews --status pending
```

## Public TACO zero-shot evaluation

```bash
python -m pip install -e ".[runtime,public-model,evaluation]"
python prepare_training_data.py --output data/taco-operational-v1
python evaluate_public.py \
  --backend omdet_turbo \
  --data data/taco-operational-v1 \
  --split test \
  --device auto \
  --output reports/generated/taco-omdet-zero-shot.json
```

TACO has no official train/test partition. The preparation command uses a
deterministic seed-42 source-group split and records annotation, manifest,
evaluated-image-set, prediction, and result checksums. The published result was
executed at commit:

`142eecf470a91d7d270b89ecdd6d3037b5a90809`

## Detector benchmark

```bash
.venv/bin/python benchmark.py \
  --backend omdet_turbo \
  --source media/taco-demo/taco-000866.jpg \
  --device cuda \
  --warmup 10 \
  --image-repeats 50 \
  --max-samples 50 \
  --output reports/generated/omdet-benchmark.json
```

## Full-pipeline latency profile

```bash
./startup.sh \
  --backend omdet_turbo \
  --source media/representative-line-video.mp4 \
  --device cuda \
  --warmup-calls 10 \
  --profile-timing \
  --no-display
```

Repeat every target-device condition at least three times. Keep the source,
runtime, precision, cooling, power mode, co-resident workload, and output path
consistent. Capture platform telemetry alongside every run.

## Validation and security checks

```bash
python -m pip install -e ".[dev]"
make validate
make security
```

## Evidence boundaries

- Public zero-shot TACO metrics are not target-camera or counting accuracy.
- Repeated images are detector timing evidence, not full-pipeline throughput.
- The warmed Jetson profiles are short repeatability and component evidence,
  not multi-hour endurance or production acceptance.
- Counts on unlabelled demonstration video are not counting-accuracy evidence.
- Any optimized or trained checkpoint must be evaluated on the same frozen
  held-out condition before release.

⚠️ AI & Data Notice: All output is AI-generated and must be independently
verified before sharing with customers or taking action.
