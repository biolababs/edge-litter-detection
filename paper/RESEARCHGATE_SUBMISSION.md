# ResearchGate submission record

## Recommended item type

Upload this manuscript as a **preprint**, not as a peer-reviewed article.
ResearchGate supports preprints and unpublished work, but the item should
remain clearly labeled until it is accepted by a journal or conference.

## Title

An Open and Reproducible Edge-AI System for Litter Detection, Multiclass
Classification, Tracking, and Counting

## Author

Abiola A. Babsalaam

## Affiliation

Independent Researcher

## Date

21 October 2026

## Abstract

Litter monitoring is often treated as an object-detection exercise, although a
deployable solution must also ingest operational video, maintain stable class
contracts, avoid repeated counting, persist evidence, support human review, and
integrate safely with collection or sorting workflows. This paper presents an
open and reproducible edge-AI system that addresses those requirements as one
portable application. The software accepts attached cameras, images, recorded
video, HTTP media, and RTSP streams. It normalizes public or custom detector
output into a common schema, applies duplicate suppression and
class-stabilized tracking, reports visible and unique-session counts, and
stores run evidence in SQLite and JSON. A browser interface exposes annotated
video, counts, review tasks, and source controls. The default operational
taxonomy contains 16 litter categories and can map uncertain or hazardous
items to human review and site-specific separation guidance. The detector is
an interchangeable component rather than the product boundary: the current
clean-clone workflow uses the public OmDet-Turbo Tiny open-vocabulary model,
while a litter-specific RF-DETR checkpoint may be trained and published later
if representative evaluation shows that adaptation is required. Preliminary
engineering validation confirms installation, real inference, persistence,
application tests, and model-only execution on NVIDIA CUDA and Apple silicon.
On an AWS g4dn.xlarge with a Tesla T4, a repeated-image OmDet-Turbo benchmark
measured 16.53 frames per second, 58.98 ms mean detector latency, 61.03 ms p95
latency, and 0.55 GiB peak allocated GPU memory. These measurements do not
establish target-domain accuracy, full-pipeline sustained performance, or
Jetson and AMD deployment performance. The paper therefore contributes a
reusable system, explicit count semantics, a safety and security boundary, and
a predeclared evaluation protocol while clearly separating verified
software evidence from pending empirical claims.

## Keywords

edge AI; litter detection; waste classification; object tracking; object
counting; open-vocabulary detection; human-in-the-loop; NVIDIA Jetson;
recycling; reproducible software

## Project links to enter

- Code: `https://github.com/biolababs/edge-litter-detection`
- Software revision:
  `0624677b72cf1d16b59a335b78d9003f2b479786`
- Software version: `0.10.1`

The manuscript has no DOI at this stage. Do not invent one. A DOI can be added
later if the software release or manuscript is archived in a DOI-issuing
repository.

## Suggested description

This systems and reproducibility preprint presents an open-source edge-AI
application for litter detection, multiclass classification, tracking,
counting, SQLite evidence, human review, and integration with cleanup vehicles
or sorting workflows. It reports preliminary engineering validation and
provides a frozen protocol for the pending target-domain and target-device
evaluation. Source code and reproduction instructions are available in the
linked GitHub repository.

## Files to upload

1. `Edge_Litter_Detection_Preprint.pdf` as the public full text.
2. Optionally retain `Edge_Litter_Detection_Preprint.docx` as the editable
   author source outside the public item.
3. Link the GitHub repository in the description and project links.

## Rights and quality checks before upload

- Confirm that the author name and affiliation are correct.
- Read the final PDF from beginning to end.
- Verify every reference, number, model name, date, and repository revision.
- Confirm the right to upload the manuscript and select the intended license.
- Keep the item labeled **preprint** and do not claim peer review.
- Do not upload private datasets, credentials, raw device inventories, or
  third-party media without redistribution permission.
- Confirm that no institution, supervisor, co-author, funding source, or
  ethics approval has been omitted.
- If an institutional MSc affiliation should appear, replace “Independent
  Researcher” only after confirming the official wording.
- If the paper is later published elsewhere, update the ResearchGate metadata,
  DOI, citation, and allowed full-text version according to the publisher's
  policy.

## Recommended release sequence

1. Review and approve the PDF.
2. Create a tagged GitHub software release from the cited commit.
3. Optionally archive that release with a DOI provider.
4. Upload the PDF to ResearchGate as a preprint.
5. Add the GitHub URL and, when available, the software DOI.
6. After field testing, publish a revised manuscript with accuracy, counting,
   power, thermal, and operational results.

## Notice

⚠️ AI & Data Notice: All output is AI-generated and must be independently
verified before sharing with customers or taking action.
