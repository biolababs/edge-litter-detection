# GitHub release plan

Proposed public location:

`github.com/biolababs/edge-litter-detection`

## Before the first public push

1. Approve a source-code license. Apache-2.0 is recommended for broad reuse and
   patent protection, but the repository owner must make the final choice.
2. Revoke the historical Roboflow key. The historical notebooks are not part
   of this repository, but the exposed credential remains a security issue.
3. Confirm that no dataset, image, model weight, machine inventory, or personal
   secret is staged.
4. Replace the current corporate Git author email with a personal or GitHub
   no-reply address and decide whether to rewrite existing local commits.
5. Keep results explicitly pending until target data and hardware tests exist.
6. Verify RF-DETR checkpoint and dataset redistribution terms separately.
7. Create the repository under `biolababs`, add the remote, push `main`, enable
   branch protection, and require the CI workflow.

## Suggested repository settings

- Name: `edge-litter-detection`
- Description: `Portable real-time litter detection, multiclass classification, tracking, and counting for edge AI devices.`
- Visibility: public only after the blocking checks pass
- Default branch: `main`
- Issues and discussions: enabled
- Secret scanning and dependency alerts: enabled
- Merge protection: CI required, no force pushes to `main`

## Release boundary

The first source release may include code, documentation, tests, and the
prospective thesis. It must not include unlicensed data or unvalidated model
weights. A later model release should carry its own model card, dataset version,
checksums, hardware results, and third-party notices.
