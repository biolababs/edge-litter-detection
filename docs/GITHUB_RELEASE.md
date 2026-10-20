# GitHub release status

Public location:

`github.com/biolababs/edge-litter-detection`

## Completed for the first public push

- Apache-2.0 was approved for the software and software documentation.
- The historical Roboflow key was revoked.
- The public tree was checked for datasets, weights, raw inventory, credentials,
  private host identifiers, and oversized artifacts.
- The public Git history uses a GitHub no-reply author identity.
- Results remain explicitly pending until target data and hardware tests exist.
- The repository was created under `biolababs`, and `main` was pushed.

RF-DETR checkpoint, dataset, image, thesis, and model-weight redistribution
terms remain separate release decisions.

## Suggested repository settings

- Name: `edge-litter-detection`
- Description: `Portable real-time litter detection, multiclass classification, tracking, and counting for edge AI devices.`
- Visibility: public
- Default branch: `main`
- Issues and discussions: enabled
- Secret scanning and dependency alerts: enabled
- Merge protection: CI required, no force pushes to `main`

## Release boundary

The first source release may include code, documentation, tests, and the
prospective thesis. It must not include unlicensed data or unvalidated model
weights. A later model release should carry its own model card, dataset version,
checksums, hardware results, and third-party notices.
