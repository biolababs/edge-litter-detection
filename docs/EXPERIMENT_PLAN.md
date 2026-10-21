# Use-case validation plan

## Question

Does the single versioned litter solution detect, classify, track, and count
litter accurately and efficiently enough for the defined operational use case?

The study evaluates the solution. It does not compare detector families or
build a leaderboard.

## Frozen implementation

The evaluated implementation is the project-maintained RF-DETR Nano litter
checkpoint, exact class schema, thresholds, tracking configuration, and runtime
revision recorded in the release manifest.

Grounding DINO is the functional bootstrap. OmDet-Turbo Tiny is a no-training
engineering acceptance candidate. Neither is a second thesis contender; the
reported study evaluates only the implementation ultimately frozen for release.

## Validation conditions

| Condition | Purpose |
|---|---|
| Frozen checkpoint checksum, class schema, and thresholds | Establish reproducible detection/classification behavior |
| Frozen grouped held-out dataset | Prevent tuning on final evaluation scenes |
| Full video application | Validate tracking, counting, persistence, and review behavior |
| Intended edge runtime | Validate latency, memory, power, temperature, and stability |

An exported artifact is checked against the same selected checkpoint for
unacceptable regression. That is runtime validation, not model comparison.

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
- record the model checksum, hardware, and runtime environment.

The provisional Jetson target is at least 15 source-to-result frames per second
under the declared coexistence condition. It is an acceptance target, not an
achieved result.

## Procedure

1. Build the attributed TACO bootstrap dataset with grouped splits.
2. Add representative field and vehicle-mounted data.
3. Supply examples for every released class and document annotation rules.
4. Freeze the class schema and a held-out test partition.
5. Train one release candidate off-device.
6. Tune thresholds and tracking using development data only.
7. Freeze configuration before opening the held-out test set.
8. Measure detection, classification, review, and count accuracy.
9. Run sustained full-application tests on the intended device.
10. Capture throughput, latency, memory, temperature, power, and failure
    evidence.
11. Publish weights only after all declared release gates pass.

Every final target-device condition will be executed at least three times
(`N >= 3`) after at least 10 detector warm-up calls. Reports will include mean, population standard
deviation, median, p95, p99, minimum, and maximum latency. A longer endurance
run is additional evidence and does not replace replication.

Before representative project data are available, the public OmDet-Turbo
checkpoint may be evaluated once on the deterministic grouped TACO test split.
That result must be labeled a zero-shot bootstrap screen rather than
target-domain or release-checkpoint accuracy.

## Results status

### Detection and classification

| Precision | Recall | F1 | mAP50 | mAP50-95 |
|---:|---:|---:|---:|---:|
| pending | pending | pending | pending | pending |

### Counting

| Frame-count MAE | Unique-count error | Duplicate-track rate | Missed-track rate |
|---:|---:|---:|---:|
| pending | pending | pending | pending | pending |

### Operational acceptance

| Runtime | FPS | p95 latency | Incremental memory | Peak temperature | Sustained run |
|---|---:|---:|---:|---:|---|
| Jetson OmDet repeated-image detector benchmark | 5.54 | 175.65 ms | 0.95 GiB observed system-available delta; 2.20 GiB max process RSS | 55.16 °C | 50 samples after 10 warm-ups |
| Jetson complete video workflow | 4.94 | not separately captured | 4,851 MB peak total Jetson RAM used | 66.31 °C | 3,622 frames / 733.54 s |

Both rows are preliminary single-run coexistence evidence. The 15 FPS target
was not met, and repeated plus multi-hour endurance runs remain pending.
Detection/classification accuracy and count error remain pending labeled
representative data.
