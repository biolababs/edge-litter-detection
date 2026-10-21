# Contributing

## Scope

This repository implements one use case with RF-DETR Nano: litter detection,
multiclass classification, tracking, counting, human-assisted separation, and
operational integration. Contributions should improve that implementation, its
portability, accuracy evaluation, persistence, documentation, or operational
safety. Model-family leaderboards are out of scope.

## Development setup

```bash
./startup.sh --list-cameras
```

Install the platform-appropriate PyTorch build before RF-DETR when using NVIDIA
CUDA, AMD ROCm, or Jetson. Advanced contributors may install the editable
extras directly when they need a customized environment.

## Required checks

```bash
make validate
```

Changes to `thesis/manuscript.md` also require:

```bash
make docx
```

Do not commit data, images, model weights, generated reports, credentials,
private network details, or personally identifiable information.

## Runtime adapters

An accelerator/runtime adapter must return the standard `Detection` schema. It
must not reimplement tracking or counting. Include:

- a documented environment and export process;
- a checksum and source checkpoint reference;
- an accuracy-equivalence check;
- unit tests using small fakes or fixtures;
- no automatic package installation or device reconfiguration.

## Reporting defects

Include the Git revision, configuration, hardware manifest, sanitized error,
input type, and whether the issue affects detection, classification, tracking,
counting, export, or deployment. Never attach private camera frames or stream
credentials to a public issue.
