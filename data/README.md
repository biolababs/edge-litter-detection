# Evaluation and maintainer training data

Data files are intentionally excluded from Git. Ordinary users do not need a
training dataset. Maintainers need licensed, representative labeled media to
build and evaluate the published RF-DETR checkpoint.

Prepare the attributed TACO COCO bootstrap automatically:

```bash
python prepare_training_data.py
```

This creates:

```text
data/taco-operational-v1/
├── classes.yaml
├── manifest.json
├── train/
│   └── _annotations.coco.json
├── valid/
│   └── _annotations.coco.json
└── test/
    └── _annotations.coco.json
```

Images are downloaded into their assigned split directories and remain ignored
by Git. The manifest records sources, licenses, checksums, mapping decisions,
group assignments, class counts, and release blockers.

For held-out test evaluation, a YOLO `data.yaml` must declare `test`, or a COCO
dataset must contain `test/_annotations.coco.json`. The evaluator fails instead
of silently reporting validation metrics as test metrics.

TACO is bootstrap data only. Add representative field data and examples for
every released class. Split new data by collection site/session before
augmentation. Do not distribute near-duplicate video frames across train,
validation, and test sets.

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

