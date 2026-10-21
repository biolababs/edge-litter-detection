# ResearchGate submission record

## Recommended item type

Upload this manuscript as a **preprint**, not as a peer-reviewed article.
ResearchGate supports preprints and unpublished work, but the item should
remain clearly labeled until it is accepted by a journal or conference.

## Title

An Open and Reproducible Edge-AI Software Architecture for Litter Detection,
Multiclass Classification, Tracking, and Counting

## Author

Abiola A. Babsalaam

## Affiliation

Independent Researcher

## Date

21 October 2026

## Manuscript version

Preprint 1.7

## Abstract

Deployable litter monitoring requires more than object detection: it must
ingest operational video, maintain stable class contracts, avoid repeated
counting, persist evidence, support human review, and integrate safely with
collection or sorting workflows. This paper presents an open and reproducible
edge-AI software architecture that packages these functions as one portable
application. It accepts cameras, images, recorded video, HTTP media, and RTSP
streams; normalizes public or custom detector output; performs duplicate
suppression and class-stabilized tracking; reports visible and unique-session
counts; stores auditable SQLite and JSON evidence; and provides a browser
interface for annotated video, counts, review, and source control.

The detector is interchangeable rather than the product boundary. A clean
clone uses a pinned public OmDet-Turbo Tiny checkpoint, while a validated
litter-specific checkpoint can later replace it without changing downstream
contracts. On a deterministic source-grouped TACO test partition of 212 images
and 680 mapped annotations, the public checkpoint measured 7.65% COCO
mAP50–95, 10.16% mAP50, and 7.49% micro F1 at a frozen operating point. The
result identifies the checkpoint as a functional bootstrap, not a
production-accepted litter classifier.

Engineering validation covers installation, inference, persistence, automated
checks, and execution on NVIDIA CUDA, Apple silicon, and a Jetson Orin Nano
8 GB. A complete 3,622-frame Jetson run measured 4.94 source-to-result FPS;
three warmed 300-frame full-pipeline repetitions measured 5.188 ± 0.010 FPS.
Model forward, preprocessing, and annotation/output accounted for 95.38% of
wall time, whereas tracking, JSONL, and SQLite together accounted for less than
1%. The provisional 15 FPS target was not met. The contribution is therefore a
reusable architecture with explicit count semantics, safety and security
boundaries, traceable preliminary evidence, and a protocol for target-domain
accuracy, counting, endurance, and hardware acceptance work that remains
pending.

## Keywords

edge AI; litter detection; waste classification; object tracking; object
counting; open-vocabulary detection; human-in-the-loop; NVIDIA Jetson;
recycling; reproducible software

## Project links to enter

- Code: `https://github.com/biolababs/edge-litter-detection`
- Software revision:
  `9f0c651ae455dabc8e5a3ebcf18f43a1639bae32`
- Software version: `0.11.0`

The manuscript has no DOI at this stage. Do not invent one. A DOI can be added
later if the software release or manuscript is archived in a DOI-issuing
repository.

## Suggested description

This systems and reproducibility preprint presents an open-source edge-AI
application for litter detection, multiclass classification, tracking,
counting, SQLite evidence, human review, and integration with cleanup vehicles
or sorting workflows. It reports a grouped public-data zero-shot accuracy
screen and replicated Jetson full-pipeline profiling. The low public-model
accuracy and sub-target Jetson throughput are reported as findings, while
target-domain accuracy, count error, endurance, AMD validation, and operational
outcomes remain open. Source code and reproduction instructions are available
in the linked GitHub repository.

## Files to upload

1. `Edge_Litter_Detection_Preprint.pdf` as the public full text.
2. Optionally retain `Edge_Litter_Detection_Preprint.docx` as the editable
   author source outside the public item.
3. Link the GitHub repository in the description and project links.

The V1.7 PDF uses a neutral single-column journal-preprint layout and contains
seven deterministic vector figures covering architecture, count semantics,
the machinery-safety boundary, model adaptation, evaluation, the measured
Jetson latency profile, and the leading TACO class-confusion pairs.

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
6. After target-domain labeling, count evaluation, endurance, optimization,
   and field testing, publish a revised manuscript with operational accuracy,
   reliability, and outcome results.
