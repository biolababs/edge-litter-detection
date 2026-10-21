# Software and research separation

The public application and the MSc evaluation are related but independent
deliverables.

| Area | Reusable software | Research work |
|---|---|---|
| Purpose | Detect, classify, track, count, review, persist, and integrate litter observations | Evaluate whether a versioned system meets defined accuracy and edge-device requirements |
| Location | `src/`, `config/`, `deploy/`, `schemas/`, and operational docs | `thesis/` and experiment documents |
| License | Apache-2.0 for original project code and software documentation | Academic text, datasets, weights, and results can have separate terms |
| Default model | Public Grounding DINO Tiny, downloaded automatically | The same frozen public-model configuration can be evaluated |
| Custom training | Optional advanced profile | Optional research extension, not a prerequisite |
| Claims | Implemented interfaces and behavior | Measured accuracy, latency, memory, power, and limitations |

## What a user can do immediately

A user can clone the repository and run:

```bash
./startup.sh --source 0
```

The launcher installs the public-model runtime, downloads and caches the model,
processes the selected source, writes evidence, and stores counts in SQLite.
No thesis manuscript, dataset, API key, or custom checkpoint is required.

The default class catalog contains 16 configurable prompts. Because the default
detector is open-vocabulary, users can change `config/classes.yaml` without
retraining. Output names should be treated as versioned API/database
identifiers.

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

## Optional specialization

A team with licensed target-domain data may choose to train a closed-set
RF-DETR checkpoint. This can be useful when the public zero-shot profile does
not meet local accuracy or performance targets. That is an optimization path,
not the normal installation requirement.

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

The thesis can report the public Grounding DINO Tiny configuration as the
implementation baseline. Optional custom training can be documented later as
future optimization or an additional implementation phase without making the
public software depend on it.
