# Software and research separation

The repository is both a reusable software project and the reference
implementation for an MSc study. Those deliverables have different readiness
and release rules.

| Area | Reusable software | Research work |
|---|---|---|
| Purpose | Run detection, classification, tracking, counting, human review, separation guidance, persistence, APIs, and evidence output | Evaluate accuracy and edge-device operation |
| Location | `src/`, `config/`, `deploy/`, `schemas/`, and operational docs | `thesis/` and experiment documents |
| License | Apache-2.0, subject to `LICENSE-NOTICE.md` | Separate academic and artifact rights |
| Data | User-supplied input media | Frozen, licensed study dataset |
| Model | Compatible trained checkpoint supplied by the user or project release | Checkpoint trained and frozen for the study |
| Claims | Interfaces and implemented behavior | Measured accuracy, latency, memory, power, and limitations |

## What users can reuse

Users can clone the repository, run `startup.sh`, inspect cameras or other
inputs, install a verified checkpoint, run the CLI or API, and consume the
documented JSON schema. SQLite persistence, vehicle/route context, the human
review queue, and integration outbox are part of the reusable software. None of
those operations require the thesis manuscript.

The default application classes are:

1. glass;
2. metal;
3. paper/cardboard;
4. plastic;
5. other litter.

A checkpoint must use the same class IDs and names as `config/classes.yaml`.

## What remains pending

The project does not yet distribute its own trained litter checkpoint, dataset,
or measured target-device results. Until those artifacts exist, the public
repository should be described as:

> The reusable application code for real-time litter detection,
> classification, tracking, and counting. A trained project checkpoint and
> measured research results are pending.

It should not yet be described as a validated litter model or as achieving a
specific accuracy, frame rate, memory footprint, or power target.

After validation and redistribution approval, the release URL and SHA-256 are
recorded in `config/model-release.json`. That turns the standard workflow into
`git clone` followed by `./startup.sh`; the launcher installs and verifies the
model automatically.

## Reproducible thesis use

Each thesis experiment should record:

- Git commit;
- class schema version;
- dataset version and checksum;
- trained checkpoint checksum;
- export/runtime artifact checksum;
- configuration and confidence threshold;
- device and software manifest;
- raw evidence and analysis output.

This allows the thesis to state that a specific version of the public software
was used without making the software repository depend on the manuscript.
