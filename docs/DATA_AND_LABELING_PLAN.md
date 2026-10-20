# Data and labeling plan

## Goal

Build a dataset that measures litter detection in the intended deployment
conditions, not merely performance on randomly mixed internet images.

## Data sources

Use two clearly separated categories:

- **Public seed data:** licensed litter datasets used for initialization and
  coverage.
- **Target-domain data:** images collected with the intended or comparable
  camera across representative sites and conditions.

For every source, record the license, citation, download date, version, image
count, annotation format, and any restrictions on redistribution.

## Provisional taxonomy

| Class | Include | Exclude or mark ambiguous |
|---|---|---|
| glass | visible bottles, jars, fragments when visually supportable | transparent object with uncertain material |
| metal | cans and clearly metallic litter | foil-like item with uncertain material |
| paper/cardboard | paper, cartons, cardboard packaging | fabric or plastic wrappers |
| plastic | bottles, cups, bags, rigid plastic | material cannot be distinguished |
| other litter | litter outside the four material groups | natural debris and permanent street objects |

Material cannot always be inferred from pixels. Annotators must use
`other_litter` or an exclusion flag instead of guessing.

## Collection matrix

Collect across:

- morning, midday, evening, and low light;
- sunny, cloudy, wet, and—if relevant—snowy conditions;
- clean and cluttered backgrounds;
- sidewalks, parks, parking areas, transit areas, and bins;
- object sizes, viewing angles, occlusion, crushing, and contamination;
- multiple camera heights and distances.

Avoid collecting identifiable people. If a person, face, plate, home address,
or precise location enters a frame, apply the approved de-identification and
retention procedure.

## Annotation

- RF-DETR-supported YOLO or COCO bounding-box format.
- One written class guide with positive, negative, and ambiguous examples.
- Annotator identifier and annotation-tool version.
- Ten to twenty percent double-annotated during the pilot.
- Resolve disagreements and update the guide before full labeling.
- Run automated checks for invalid boxes, empty labels, duplicate files,
  unknown class IDs, and boxes outside image bounds.

## Split policy

Assign collection groups to train, validation, and test before augmentation.
A collection group is a site/session/video sequence. All adjacent or
near-duplicate frames remain in one split.

Initial target:

- 70% training groups;
- 15% validation groups;
- 15% held-out test groups.

The held-out test set is frozen before accuracy evaluation. Do not tune
thresholds against it.

## Versioning

Each dataset release must include:

- semantic version;
- file manifest and checksums;
- class counts and instance counts;
- source/license inventory;
- collection and split logic;
- known gaps and biases;
- de-identification record.

