# Use-case validation plan

## Question

Does the public Grounding DINO Tiny implementation detect, classify, track, and
count litter accurately and efficiently enough for the defined operational use
case?

The study evaluates the solution. It does not compare detector families or
build a leaderboard.

## Validation conditions

| Condition | Purpose |
|---|---|
| Frozen public model ID, prompt catalog, and thresholds | Establish reproducible detection/classification behavior |
| Full video application | Validate tracking, counting, persistence, and review behavior |
| Intended edge runtime | Validate latency, memory, power, temperature, and stability |

If an optimized runtime artifact is introduced, it is checked against the same
frozen public-model configuration for unacceptable regression. That is runtime
validation, not model comparison.

## Detection and classification

- precision, recall, F1, mAP50, and mAP50-95;
- per-class results and confusion analysis;
- results by object size, lighting, weather, site type, occlusion, clutter, and
  camera distance;
- review volume and human correction rate.

## Counting

- per-frame absolute count error by class;
- visible-count mean absolute error;
- unique-run count error;
- duplicate-track and missed-track rates;
- class reassignment within a track;
- errors by motion, occlusion, density, and scene cut.

Track-level ground truth is required for identity-based count metrics. Detection
mAP cannot substitute for count validation.

## Operational acceptance

The application must:

- process the declared source reliably;
- produce boxes, classes, confidence, track IDs, counts, and timestamps;
- preserve SQLite and JSONL evidence across normal interruption;
- avoid sustained memory growth and swap-dependent operation;
- preserve declared memory for co-resident services;
- avoid sustained thermal throttling;
- record the model, prompts, hardware, and runtime environment.

The provisional Jetson target is at least 15 source-to-result frames per second
under the declared coexistence condition. It is an acceptance target, not an
achieved result.

## Procedure

1. Freeze the model revision, class schema, prompts, source inventory, and
   grouped development/test split.
2. Annotate representative images and videos, including persistent object
   identities for the count subset.
3. Refine prompts and confidence/tracking thresholds using development data
   only.
4. Freeze configuration before opening the held-out test set.
5. Measure detection, classification, review, and count accuracy.
6. Run sustained full-application tests on the intended device.
7. Capture throughput, latency, memory, temperature, power, and failure
   evidence.
8. Analyze false detections, misses, class errors, duplicate counts, missed
   counts, and track merges.
9. Consider an optimized runtime or custom model only when the measured
   baseline fails a documented acceptance requirement.

## Pending results

### Detection and classification

| Precision | Recall | F1 | mAP50 | mAP50-95 |
|---:|---:|---:|---:|---:|
| pending | pending | pending | pending | pending |

### Counting

| Frame-count MAE | Unique-count error | Duplicate-track rate | Missed-track rate |
|---:|---:|---:|---:|
| pending | pending | pending | pending |

### Operational acceptance

| Runtime | FPS | p95 latency | Incremental memory | Peak temperature | Sustained run |
|---|---:|---:|---:|---:|---|
| pending | pending | pending | pending | pending | pending |
