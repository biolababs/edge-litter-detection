# Evaluation and optional custom-model data

Data files are intentionally excluded from Git. The public Grounding DINO
profile does not need a training dataset, but representative labeled media is
required to measure detection and counting accuracy.

If a team chooses the optional RF-DETR training profile, an expected YOLO
layout is:

```text
data/litter/
├── data.yaml
├── images/
│   ├── train/
│   ├── val/
│   └── test/
└── labels/
    ├── train/
    ├── val/
    └── test/
```

RF-DETR accepts YOLO-format data when `data.yaml` is present at the dataset
root. A COCO-format dataset is also supported. The frozen data manifest must
state which format and schema version were used.

For held-out test evaluation, a YOLO `data.yaml` must declare `test`, or a COCO
dataset must contain `test/_annotations.coco.json`. The evaluator fails instead
of silently reporting validation metrics as test metrics.

Split by collection site/session before augmentation. Do not randomly distribute
near-duplicate video frames across train, validation, and test sets.

## Counting evaluation

Copy `count-ground-truth.example.json` to an ignored data path such as
`data/count-ground-truth.json`. Annotate representative frame indices with
visible counts and, when the complete session has been reviewed, the unique
session count. The schema is `schemas/count-ground-truth.schema.json`.

Run the application on the same unmodified video, then evaluate:

```bash
python evaluate_counts.py \
  --events reports/generated/session-events.jsonl \
  --ground-truth data/count-ground-truth.json
```

Aggregate count annotations support visible-count and unique-session count
accuracy. Duplicate-track, missed-track, and identity-switch analysis requires
persistent object IDs in a richer track-level annotation.

