# Model card: public edge litter profile

## Status

The repository's default runnable profile uses the public
`IDEA-Research/grounding-dino-tiny` checkpoint through Hugging Face
Transformers. It is an open-vocabulary reference implementation and does not
require project-specific training.

The model is public, but this repository does not redistribute its weights.
Transformers downloads the selected revision from its source and stores it in
the local user cache. Review the upstream model card and terms before
production or redistribution.

## Intended use

Detect and classify visible litter in images or video to support:

- cleanup route observation and counting;
- worker-assisted litter identification;
- configurable separation guidance;
- fixed-camera environmental monitoring;
- perception input to a larger truck or fleet system.

The application reports visible detections and unique confirmed track IDs.
Counting accuracy must be validated independently of detection accuracy.

## Default operational catalog

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

This is not a fixed output layer. Operators can revise the prompts without
training. Stable output names should be versioned when databases or external
consumers depend on them.

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

## Optional specialized model

The repository also contains an RF-DETR adapter and training/evaluation
utilities for teams that choose to create a licensed, target-specific
closed-set model. That profile is optional and has its own data, checkpoint,
license, and validation requirements.

## Upstream references

- Grounding DINO repository: https://github.com/IDEA-Research/GroundingDINO
- Public checkpoint:
  https://huggingface.co/IDEA-Research/grounding-dino-tiny
- Transformers documentation:
  https://huggingface.co/docs/transformers/model_doc/grounding-dino
