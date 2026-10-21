# Model card: edge litter detector

## Status

The selected release detector is a project-maintained RF-DETR Nano checkpoint.
Its artifact is not published yet because representative data, complete class
coverage, held-out accuracy, counting accuracy, and target-device validation
are still pending.

The repository's current runnable bootstrap uses the public
`IDEA-Research/grounding-dino-tiny` checkpoint through Hugging Face
Transformers. It is an open-vocabulary reference implementation and does not
require project-specific training. It exercises the complete application but
is not the production-accuracy claim.

The repository also integrates the Apache-2.0
`omlab/omdet-turbo-swin-tiny-hf` checkpoint as a confidence-scored
open-vocabulary acceptance candidate. These public models are downloaded by
Transformers and stored in the local user cache; this repository does not
redistribute their weights.

## Intended use

Detect and classify visible litter in images or video to support:

- cleanup route observation and counting;
- worker-assisted litter identification;
- configurable separation guidance;
- fixed-camera environmental monitoring;
- perception input to a larger truck or fleet system.

The application reports visible detections and unique confirmed track IDs.
Counting accuracy must be validated independently of detection accuracy.

## Operational catalog

The default configuration contains 16 prompts:

1. plastic bottle;
2. glass bottle;
3. metal can;
4. paper;
5. cardboard;
6. plastic bag;
7. food wrapper;
8. disposable cup;
9. cigarette butt;
10. food waste;
11. textile;
12. tire;
13. battery;
14. electronic waste;
15. broken glass; and
16. other litter.

The output names and IDs are stable interfaces for the database and external
consumers. Bootstrap prompts can be revised without training. The release
checkpoint uses a fixed output layer and must exactly match the published class
schema.

## Human review

Low-confidence detections and configured hazardous or ambiguous categories
enter a review queue. Separation destinations are operator guidance, not a
universal determination of material composition or recyclability.

## Out-of-scope use

- facial recognition, person re-identification, or behavior scoring;
- license-plate recognition or automated enforcement;
- hazardous-material certification based only on an image;
- autonomous collection-arm actuation without an independent safety system;
- claims that all configured prompts have equal or validated accuracy;
- deployment without representative accuracy and operational testing.

## Known limitations

- small, occluded, crushed, transparent, reflective, or dirty litter;
- visual ambiguity between materials and object types;
- overlapping prompts that can describe the same object;
- domain shift across cameras, cities, seasons, weather, and time of day;
- false positives on non-litter objects;
- duplicate counts after long occlusion, scene cuts, or re-entry;
- latency and memory differences across CPU, NVIDIA, AMD, and Jetson targets.

The adapter applies class-agnostic non-maximum suppression to reduce duplicate
boxes produced by overlapping text prompts. This does not eliminate every
semantic conflict.

## Evaluation

Report at minimum:

- precision, recall, F1, mAP50, mAP50-95, and per-class results;
- errors by object size and scene condition;
- per-frame visible-count error;
- unique-session count error and duplicate-track rate;
- sustained throughput and p50/p95 latency;
- process and system memory;
- temperature, power, and throttling on the target edge device;
- review volume and operator correction patterns.

No accuracy, frame-rate, memory, or power result is claimed until the relevant
measurement is completed.

## Release artifact requirements

The RF-DETR release remains blocked until it has:

- training and held-out examples for every released class;
- a versioned data statement and source/license inventory;
- detection, classification, and count evaluation evidence;
- sustained edge-device latency, memory, power, and thermal evidence;
- a public artifact URL and SHA-256 digest;
- a successful clean-clone automatic-download test.

## Upstream references

- Grounding DINO repository: https://github.com/IDEA-Research/GroundingDINO
- Public checkpoint:
  https://huggingface.co/IDEA-Research/grounding-dino-tiny
- Transformers documentation:
  https://huggingface.co/docs/transformers/model_doc/grounding-dino
- OmDet-Turbo checkpoint:
  https://huggingface.co/omlab/omdet-turbo-swin-tiny-hf
- Transformers OmDet-Turbo documentation:
  https://huggingface.co/docs/transformers/model_doc/omdet-turbo
- RF-DETR repository: https://github.com/roboflow/rf-detr
- TACO repository: https://github.com/pedropro/TACO
