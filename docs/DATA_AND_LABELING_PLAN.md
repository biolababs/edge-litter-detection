# Data and labeling plan

## Goal

Create the evidence and training data needed for one reusable litter solution.
End users do not train; maintainers publish a validated model that the launcher
downloads automatically.

## Automated TACO bootstrap

Run:

```bash
python prepare_training_data.py
```

The command creates ignored local data under `data/taco-operational-v1/` with:

- COCO `train`, `valid`, and `test` directories;
- deterministic source-group splits;
- conservative mapping to the operational taxonomy;
- annotations and image checksums;
- per-image source and license metadata;
- a complete source-category mapping;
- an explicit list of product classes with no instances.

The generated manifest labels this data as bootstrap-only. A trained artifact
is not release-ready merely because TACO preparation or training completes.

## Operational catalog

The configuration contains:

- plastic bottle, glass bottle, and metal can;
- paper and cardboard;
- plastic bag, food wrapper, and disposable cup;
- cigarette butt and food waste;
- textile and tire;
- battery, electronic waste, and broken glass;
- other litter.

TACO does not provide representative coverage for every product class or every
deployment condition. Missing categories must be supplied through licensed
field data or removed from the released taxonomy. They must not remain as
random, untrained output classes.

## Field-data matrix

Include:

- morning, midday, evening, and low light;
- dry, wet, cloudy, and locally relevant seasonal conditions;
- clean and cluttered backgrounds;
- sidewalks, parks, parking areas, transit areas, roadsides, and bin areas;
- object sizes, angles, occlusion, crushing, contamination, and motion blur;
- representative truck camera heights, distances, speeds, and lenses;
- human-assisted sorting scenes when that workflow is in scope.

Minimize capture of identifiable people, plates, addresses, and unnecessary
location data. Apply the approved de-identification and retention process.

## Annotation

- COCO bounding boxes with stable class IDs.
- One written guide with positive, negative, and ambiguous examples.
- Persistent object IDs for videos used to score unique counts.
- Annotator and tool version.
- A double-annotated subset for agreement and guide refinement.
- Automated checks for invalid boxes, corrupt media, duplicate files, unknown
  IDs, and out-of-bounds coordinates.

Material must not be guessed when visual evidence is insufficient. Route
uncertain objects to `other_litter` or exclude them according to the frozen
annotation guide.

## Split policy

Group by source collection, site, session, route, or source video before
assignment. Adjacent and near-duplicate frames remain in one group.

Use:

- training data for parameter learning;
- validation data for checkpoint and threshold decisions;
- a frozen held-out test partition for final accuracy reporting.

The held-out test manifest is checksummed before final evaluation and is not
reused for model selection.

## Versioning

Each data release records:

- semantic version and checksums;
- image, video, class, and instance counts;
- source and license inventory;
- grouping and split logic;
- annotation agreement;
- known gaps and biases;
- de-identification record.
