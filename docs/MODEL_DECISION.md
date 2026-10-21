# Detector strategy

## Decision

Use public Grounding DINO Tiny as the default detector for the reusable
application.

This decision makes a fresh clone useful without requiring every user to build
a dataset, train a model, obtain a private checkpoint, or configure an API key.
The model is loaded through Hugging Face Transformers and cached locally after
the first download.

The application remains a single litter use case, not a model-comparison
project. RF-DETR is retained only as an optional closed-set profile for teams
that later choose to create or license a specialized checkpoint.

## Why an open-vocabulary default

An open-vocabulary detector accepts text labels at inference time. Therefore:

- the operational catalog is not limited to the five thesis-planning classes;
- class prompts can be revised without changing code;
- a municipality or operator can add locally relevant litter categories;
- the standard tracking, counting, persistence, review, and integration layers
  work before custom training data exists.

The versioned output names and detector prompts are separate in
`config/classes.yaml`. Stable output names support databases and APIs while
prompts can be tuned for the target environment.

## Default catalog

The repository supplies 16 practical prompts covering containers, paper,
packaging, cigarette waste, organics, textiles, tires, batteries, electronic
waste, broken glass, and other litter.

This catalog is a starting operational policy, not a claim that visual
appearance always reveals material composition. Batteries, electronic waste,
broken glass, generic litter, and low-confidence results enter the human
review workflow.

## Use-case acceptance

The implementation is assessed on whether it:

1. detects visible litter with a bounding box;
2. assigns a configured operational category;
3. maintains a stable track while an item remains visible;
4. reports current visible counts;
5. counts confirmed track IDs once per run;
6. persists evidence and review records offline;
7. exposes integration events to a truck or fleet system; and
8. operates within the measured limits of the target device.

Accuracy, latency, memory, sustained throughput, and failure conditions must be
measured using representative scenes. Open-vocabulary capability does not make
those measurements unnecessary.

## Operational profiles

### Public profile

- Backend: `grounding_dino`
- Model: `IDEA-Research/grounding-dino-tiny`
- Training required: no
- API key required: no
- Classes: configured as text prompts
- Intended role: immediate reusable baseline and reference deployment

### Optional specialized profile

- Backend: `rfdetr`
- Model: user-supplied compatible checkpoint
- Training required: only if the organization chooses to create a custom model
- Classes: fixed by the checkpoint
- Intended role: later accuracy, size, latency, or export optimization

These profiles are implementation choices for the same product workflow. The
project does not rank model families or publish a leaderboard.

## LLM/VLM role

An LLM is not needed in the continuous detection, tracking, or counting loop.
Language prompts configure the Grounding DINO detector, but a separate
generative LLM service is not required.

## Primary references

- Grounding DINO repository: https://github.com/IDEA-Research/GroundingDINO
- Grounding DINO Tiny model card:
  https://huggingface.co/IDEA-Research/grounding-dino-tiny
- Transformers Grounding DINO documentation:
  https://huggingface.co/docs/transformers/model_doc/grounding-dino
- RF-DETR repository: https://github.com/roboflow/rf-detr
