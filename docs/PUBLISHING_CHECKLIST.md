# Publication checklist

## Blocking before the public source-code release

- [x] Approve Apache-2.0 or select another source-code license.
- [x] Revoke the Roboflow key embedded in the historical notebooks.
- [x] Use a personal/GitHub no-reply Git author identity instead of the current
      corporate email; rewrite unpublished local history if desired.
- [x] Confirm no dataset, model weight, raw machine inventory, generated report,
      credential, or private image is staged.
- [x] Secret scan, unit tests, syntax checks, and release validation pass.
- [ ] Independently verify public documentation and technical claims.

The source release can state that representative accuracy and device results
are pending. It must not imply that the public model has already been validated
for every deployment.

## Blocking before the validated research/model release

- [x] Confirm the Jetson hardware and software baseline through a read-only
      inventory.
- [x] Automate TACO source, checksum, category mapping, split, and per-image
      license manifests.
- [ ] Complete independent dataset-license and required-attribution review.
- [ ] Complete ethics/privacy review for new camera data.
- [ ] Freeze the class schema, dataset version, and held-out split.
- [ ] Annotate track-level ground truth for counting evaluation.
- [x] Select RF-DETR Nano as the single release architecture.
- [ ] Train and freeze the project checkpoint and exact class schema.
- [x] Prepare detection/classification and aggregate counting evaluators.
- [ ] Run detection/classification and counting accuracy evaluation.
- [ ] Recapture the Jetson inventory before the authorized validation run.
- [ ] Obtain a test window that does not disrupt the existing project.
- [ ] Complete operational acceptance checks.
- [ ] Replace every `pending` result with measured evidence or retain an
      explicit limitation.

## GitHub repository

- [x] Create `biolababs/edge-litter-detection`.
- [x] Add the Git remote without storing credentials in its URL.
- [x] Push `main`.
- [ ] Require the CI workflow for protected changes.
- [ ] Enable secret scanning and dependency alerts.
- [ ] Protect `main` from force pushes.
- [x] Complete `CITATION.cff`, model card, changelog, and source license.
- [ ] Tag the source release with a semantic version.

## Artifact release

- [ ] Record evaluation data, selected model revision, selected export, and
      environment checksums.
- [ ] Publish large weights as release assets or through an appropriate model
      registry, not normal Git blobs.
- [ ] Attach the model card, dataset statement, target accuracy, counting
      accuracy, hardware manifest, and limitations.
- [ ] Archive a permanent release through Zenodo or an institutional repository
      when the academic work is ready.
