# Use-case validation plan

## Question

Does the RF-DETR Nano implementation detect, classify, track, and count litter
accurately enough for the defined edge-monitoring use case?

This study does not compare model families or build a model leaderboard.

## Validation conditions

| Condition | Purpose |
|---|---|
| RF-DETR Nano source checkpoint | Establish test-set detection/classification accuracy |
| Target runtime artifact | Verify exported-model accuracy is retained |
| Full video application | Validate tracking, counting, and operational behavior |

All conditions use the same dataset schema and frozen held-out test material.
An exported artifact is checked against its source checkpoint to detect
conversion regressions, not to declare one model better than another.

## Detection and classification accuracy

- mAP50-95 and mAP50;
- per-class AP;
- precision, recall, and F1 at the declared operating threshold;
- confusion matrix;
- performance by object size;
- errors by lighting, weather, site type, occlusion, clutter, and camera
  distance.

## Counting accuracy

- per-frame absolute count error by class;
- mean absolute error across frames;
- unique-session count error by class;
- duplicate-track rate;
- missed-track rate;
- class reassignment rate within a track;
- count error by camera motion, occlusion, density, and scene cut.

Counting ground truth will be annotated at the track/session level on a
representative video subset. Detection mAP cannot substitute for count
validation.

## Operational acceptance

The application must:

- process the declared input source reliably;
- produce boxes, classes, confidence, track IDs, counts, and timestamps;
- retain streaming JSONL evidence if the process is interrupted;
- avoid sustained memory growth and swap-dependent operation;
- preserve sufficient memory for other services on a shared device;
- avoid sustained thermal throttling;
- clearly record the hardware and runtime environment.

The provisional Jetson target is at least 15 source-to-result frames per second
under the declared coexistence condition. This is an application acceptance
target, not a comparison metric and not an achieved result.

## Procedure

1. Freeze the class schema, data version, and site/session-level split.
2. Annotate a representative video subset with persistent ground-truth object
   identities for count evaluation.
3. Train RF-DETR Nano using training and validation data only.
4. Choose confidence and tracking thresholds using validation data.
5. Freeze the checkpoint, thresholds, and test protocol.
6. Evaluate detection and classification accuracy once on the held-out test
   set.
7. Evaluate visible and unique-session count accuracy on the track-annotated
   video subset.
8. Export the frozen checkpoint for the intended edge runtime.
9. Confirm that export does not create an unacceptable accuracy regression.
10. Run a sustained full-application test and capture the environment,
    throughput, memory, temperature, and failure evidence.
11. Analyze false detections, missed detections, class errors, duplicate counts,
    missed counts, and track merges.

The repository supplies `evaluate.py` for the frozen RF-DETR checkpoint and
`evaluate_counts.py` for aggregate visible/session count annotations. Detailed
duplicate-track, missed-track, and identity-switch rates additionally require
persistent object identities in the video ground truth.

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
