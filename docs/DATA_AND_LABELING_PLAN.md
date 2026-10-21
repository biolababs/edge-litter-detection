# Evaluation data and labeling plan

## Goal

Build evidence that measures the public litter solution in its intended
deployment conditions. A custom training dataset is not required for normal
use; representative labeled data is still required to measure accuracy and
counting.

## Sources

Use licensed public litter imagery and target-domain camera data. Record each
source's license, citation, version, download or capture date, image count,
annotation format, and redistribution restrictions.

## Operational catalog

The default configuration contains:

- plastic bottle, glass bottle, and metal can;
- paper and cardboard;
- plastic bag, food wrapper, and disposable cup;
- cigarette butt and food waste;
- textile and tire;
- battery, electronic waste, and broken glass;
- other litter.

These output categories map to configurable text prompts. Annotators should use
written inclusion, exclusion, and ambiguity rules. Material must not be guessed
when visual evidence is insufficient; uncertain items should be excluded from a
material-specific claim or routed to manual review.

## Collection matrix

Include:

- morning, midday, evening, and low light;
- dry, wet, cloudy, and locally relevant seasonal conditions;
- clean and cluttered backgrounds;
- sidewalks, parks, parking areas, transit areas, roadsides, and bin areas;
- object sizes, angles, occlusion, crushing, contamination, and motion blur;
- representative camera heights, distances, speeds, and lenses.

Minimize capture of identifiable people, plates, addresses, and unnecessary
location data. Apply the approved de-identification and retention process.

## Annotation

- COCO or YOLO bounding boxes with stable class IDs.
- One written guide with positive, negative, and ambiguous examples.
- Persistent object IDs for videos used to score unique counts.
- Annotator and tool version.
- A double-annotated subset for agreement and guide refinement.
- Automated checks for invalid boxes, corrupt media, duplicate files, unknown
  IDs, and out-of-bounds coordinates.

## Split policy

Group by site, session, route, or source video before assignment. Adjacent and
near-duplicate frames remain in one group.

Use:

- a development partition for prompt and threshold refinement; and
- a frozen held-out test partition for final accuracy reporting.

The exact ratio is chosen after the source inventory is known and must preserve
adequate class and condition coverage. The held-out test set is checksummed
before final evaluation.

## Optional custom-model data

If measured errors later justify a specialized RF-DETR profile, create a
separate training/validation/test plan. Do not silently reuse the public-model
held-out test set for model selection.

## Versioning

Each data release records:

- semantic version and checksums;
- image, video, class, and instance counts;
- source and license inventory;
- grouping and split logic;
- annotation agreement;
- known gaps and biases;
- de-identification record.
