# Detector strategy

## Decision

Use one project-maintained RF-DETR Nano checkpoint as the release detector for
the litter application.

This is a requirement-based implementation decision, not a model comparison.
The selected detector must support the fixed operational taxonomy, public
weight distribution, checksum verification, edge-oriented export, and a
runtime that fits the truck, sorting, and monitoring workflows.

Ordinary users do not train. Project maintainers prepare licensed data, train
the checkpoint centrally, evaluate it, publish a versioned artifact, and update
`config/model-release.json`. The launcher then downloads and verifies the
artifact automatically.

## Current bootstrap state

Grounding DINO Tiny remains the automatically downloaded functional bootstrap
until the project checkpoint is published. It allows any contributor to test:

- camera, image, video, and stream ingestion;
- detection normalization, tracking, and counting;
- SQLite persistence and queries;
- the human-review queue;
- annotated evidence and integration events.

The bootstrap is not the production accuracy claim. Open-vocabulary prompts
are useful for rapid functional work and data review, but the release gate is
the measured performance of the litter-specific checkpoint.

OmDet-Turbo Tiny is integrated as a stronger no-training acceptance candidate.
It is a compact Apache-2.0 open-vocabulary detector with direct confidence
scores and backend-specific prompts. It uses the complete product runtime but
does not become the release detector unless representative accuracy, counting,
and edge-device gates pass.

## Operational catalog

The stable product catalog contains 16 categories covering containers, paper,
packaging, cigarette waste, organics, textiles, tires, batteries, electronic
waste, broken glass, and other litter.

A released closed-set checkpoint must use the exact class ID/name mapping
recorded in `config/classes.yaml`. No class can be advertised as supported when
its training and held-out evaluation coverage is missing.

## Data path

`prepare_training_data.py` creates an attributed COCO dataset from TACO:

- source images and annotations are checksummed;
- fine-grained TACO categories are conservatively mapped to product classes;
- source collection batches stay together in grouped train, validation, and
  test splits;
- image-level license metadata is retained;
- classes with no training instances are reported as release blockers.

TACO is bootstrap data. It does not replace representative vehicle-mounted,
roadside, sorting, lighting, weather, distance, blur, and occlusion data.

## Release gates

The project checkpoint becomes the normal one-command default only after it:

1. has labeled training and held-out coverage for every released class;
2. meets the frozen detection and classification acceptance criteria;
3. meets count-error requirements on track-annotated video;
4. meets sustained latency, memory, thermal, and stability requirements on the
   intended edge device;
5. includes a model card, data statement, exact class schema, and checksums;
6. downloads successfully through the standard launcher.

## LLM/VLM role

An LLM is not required in the continuous detection, tracking, or counting loop.
A language or open-vocabulary model can assist maintainers with data discovery
or review, but it is not required on every deployed edge device.

## Primary references

- RF-DETR repository: https://github.com/roboflow/rf-detr
- RF-DETR documentation: https://rfdetr.roboflow.com/
- TACO repository: https://github.com/pedropro/TACO
- Grounding DINO repository: https://github.com/IDEA-Research/GroundingDINO
- OmDet-Turbo checkpoint:
  https://huggingface.co/omlab/omdet-turbo-swin-tiny-hf
