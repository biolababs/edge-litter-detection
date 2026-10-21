# Software and research separation

The public application and the MSc evaluation are related but independent
deliverables.

| Area | Reusable software | Research work |
|---|---|---|
| Purpose | Detect, classify, track, count, review, persist, and integrate litter observations | Evaluate whether a versioned system meets defined accuracy and edge-device requirements |
| Location | `src/`, `config/`, `deploy/`, `schemas/`, and operational docs | `thesis/` and experiment documents |
| License | Apache-2.0 for original project code and software documentation | Academic text, datasets, weights, and results can have separate terms |
| Detector | Grounding DINO bootstrap, OmDet-Turbo no-training screen, and published RF-DETR Nano fallback release path | Only the final frozen release configuration is evaluated |
| Training | Maintainers publish weights; deployers do not train | Training is an implementation step, not a model-comparison study |
| Claims | Implemented interfaces and behavior | Measured accuracy, latency, memory, power, and limitations |

## What a user can do immediately

A user can clone the repository and run:

```bash
./startup.sh --source 0
```

The launcher installs the runtime, downloads and caches the current model,
processes the selected source, writes evidence, and stores counts in SQLite.
No thesis manuscript, dataset, API key, or custom checkpoint is required.

The product catalog contains 16 stable output names. Grounding DINO and
OmDet-Turbo prompts can be changed without training. A published closed-set
checkpoint must use the exact class schema recorded with its release.

## What remains deployment-specific

The software is usable before project-specific training, but each deployment
must still validate:

- relevant litter categories and prompt wording;
- representative weather, lighting, camera angle, speed, and object size;
- confidence thresholds and human-review policy;
- tracking and count error;
- sustained throughput, memory, temperature, and power;
- privacy, retention, and third-party model terms.

Until those measurements exist, the repository must not claim a universal
accuracy, frame rate, memory footprint, or safety rating.

## Central model release

Maintainers train one closed-set RF-DETR Nano litter checkpoint using licensed
bootstrap and target-domain data. They publish weights only after the declared
accuracy, counting, and target-device gates pass. This is not a task for normal
deployers.

If a custom artifact is produced, record:

- source and license for the dataset;
- dataset version and checksum;
- class schema and annotation rules;
- training configuration and Git commit;
- checkpoint and exported-artifact checksums;
- threshold and runtime configuration;
- target-device manifest;
- accuracy and count evaluation evidence.

## MSc use

The thesis should evaluate a frozen version of the practical application. The
research question is whether the solution meets the defined litter use case on
representative data and target hardware—not which detector wins a model
competition.

The thesis evaluates the frozen litter-specific release implementation.
Grounding DINO can be described as an engineering bootstrap and data-review
aid, not as a competing thesis model.
