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

Public and custom model weights, datasets, images, thesis material, and derived
artifact redistribution terms remain separate release decisions.

## Suggested repository settings

- Name: `edge-litter-detection`
- Description: `Portable real-time litter detection, multiclass classification, tracking, and counting for edge AI devices.`
- Visibility: public
- Default branch: `main`
- Issues and discussions: enabled
- Secret scanning and dependency alerts: enabled
- Merge protection: CI required, no force pushes to `main`

## Release boundary

The source release includes code, documentation, tests, and the prospective
thesis. The public default model is downloaded from its upstream source rather
than committed to Git. Any later custom model release should carry its own
model card, dataset version, checksums, hardware results, and third-party
notices.
