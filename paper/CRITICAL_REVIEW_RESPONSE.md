# Response to critical preprint review

Review incorporated: 21 October 2026

Manuscript revision: preprint 1.7

## Overall response

The second review correctly identified preliminary accuracy and Jetson
component timing as the two highest-impact gaps. Revision 1.2 addressed both
with traceable evidence, and revision 1.3 added the publication-quality visual
architecture. Revision 1.4 responds to the third review by recording exact
prompts, adding reproducible cross-class diagnostics and a seventh figure,
analyzing zero-AP classes without assigning unsupported causes, separating MPS
accuracy repeatability from performance evidence, verifying the DWaste
published record, and removing the duplicate editorial AI banner. It does not
convert those results into a production claim: the measured public checkpoint
accuracy is low, count accuracy remains unmeasured, and the Jetson path remains
below the 15 FPS target.

Revision 1.7 replaces the report-style visual treatment with a conventional
single-column journal-preprint format. All seven figures are regenerated from
deterministic source as restrained vector diagrams and scientific plots with
consistent typography, line weights, notation, and grayscale-compatible color.

## Point-by-point disposition

| Review concern | Revision action | Status |
|---|---|---|
| No empirical accuracy evaluation | Added a deterministic source-grouped TACO test partition, COCO AP/AR, operating-point precision/recall/F1, support, per-class AP, checksums, and full predictions for one frozen OmDet-Turbo configuration. The result is 0.0765 mAP50–95, 0.1016 mAP50, and 0.0749 micro F1. | Addressed as preliminary public-data evidence; target-domain accuracy remains open |
| No Jetson latency breakdown | Added three 300-frame full-pipeline profiles after 10 warm-up calls each. Model forward averaged 71.10% of wall time, preprocessing 13.69%, annotation/output 10.59%, and tracking plus JSONL plus SQLite 0.91%. | Addressed |
| Benchmark variance and replication | The warmed Jetson condition was repeated three times: 5.1748, 5.1881, and 5.2002 FPS, with mean 5.1877 and population standard deviation 0.0104 FPS. The benchmark utility now reports standard deviation and p99. | Addressed for the new Jetson profile; historical T4 result remains narrow |
| Grounding DINO reference | Replaced the arXiv-only citation with the ECCV 2024 Springer proceedings citation and DOI. | Addressed |
| DINO reference | Replaced the arXiv-only record with the archival ICLR 2023 citation and official OpenReview record. | Addressed |
| ZeroWaste reference | Replaced the arXiv DOI with the CVPR 2022 proceedings record and page range. | Addressed |
| RoLID-11K reference | Replaced the arXiv-only record with the WACV Workshops 2026 proceedings citation and page range. | Addressed |
| PyTorch reference | Added the official NeurIPS proceedings record and corrected page range; the proposed `10.5555/3454287.3455008` identifier was not used because it does not resolve through DOI.org. | Addressed |
| OWASP ASVS version | Updated the cited security-verification standard from ASVS 4.0.3 to ASVS 5.0.0. | Addressed |
| RF-DETR reference | Updated the reference to its ICLR 2026 publication while retaining the arXiv identifier. | Addressed |
| Weak Litterati evidence | Added Watkins et al. (2024), which compares Litterati app data with municipal audits and reports both composition agreement and spatial sampling limitations. | Addressed |
| Missing recent integrated systems | Added DWaste and the 2026 privacy-aware smart-city trash/face application to related work. | Addressed selectively; weak or non-archival surveys were not used as principal evidence |
| Tracker motion failure boundary | Added an image-plane derivation showing that IoU ≥ 0.30 permits at most 0.538 object widths of horizontal displacement per processed frame in the simplified equal-box case. The paper explicitly refuses to convert this to vehicle speed without calibration. | Addressed analytically; field validation remains open |
| Repository-style appendices | Removed the command appendices from the main manuscript and moved exact commands and evidence boundaries to `SUPPLEMENTARY_REPRODUCIBILITY.md`. | Addressed |
| Unusual AI banner | Replaced the standalone editorial banner with a “Use of AI tools” declaration. | Addressed subject to destination-venue policy |
| Insufficient or poorly rendered diagrams | Added six editable SVG publication figures covering the system architecture, count semantics, machinery-safety boundary, model lifecycle, evaluation workflow, and measured Jetson latency profile. The same figures are embedded in the regenerated DOCX/PDF and relevant GitHub documentation. | Addressed |
| Public-model dependency security | Moved the maintained public-model path to Transformers 5.20+, declared the PyTorch 2.6+/torchvision 0.21+ floor, added an incompatibility guard, and repeated Jetson profiling with PyTorch 2.7.0 and Transformers 5.20.2 in an isolated digest-pinned container. A later network-disabled Jetson smoke passed with a read-only model cache. | Addressed for the maintained dependency line |
| Exact evaluation prompts not disclosed | Added all 16 frozen OmDet-Turbo prompt strings to the manuscript and machine-readable accuracy evidence. | Addressed |
| Zero-AP classes insufficiently analyzed | Added class-specific analysis for `cigarette_butt`, `cardboard`, `broken_glass`, and `other_litter`, while separating observed evidence from candidate causes that require ablation. | Addressed without unsupported causal claims |
| No class-confusion analysis | Added score-ordered greedy all-class matching at IoU 0.50, the top ten confusion pairs, machine-readable full pair counts, a unit test, and Figure 6. | Addressed as a diagnostic, not a replacement for COCO AP |
| MPS reproducibility caveat | Repeated the frozen evaluation on the same MPS host. Predictions were byte-identical and accuracy was unchanged, while latency differed materially. The paper now requires CUDA reproduction before a platform-independent accuracy claim. | Addressed within available hardware; CUDA accuracy cross-validation remains open |
| DWaste published-record verification | Confirmed that DOI `10.32604/jai.2026.076674` resolves to the 2026 Journal on Artificial Intelligence article and retained the arXiv identifier as the preprint record. | Addressed |
| Residual AI warning banner | Removed the duplicate warning banner from the manuscript and publication-package documents; the venue-adaptable “Use of AI tools” declaration remains. | Addressed |

## Evidence interpretation

The new accuracy result is not evidence that the current public checkpoint is
ready for field deployment. It is evidence that the checkpoint should remain a
software bring-up, review, and data-collection model until a frozen
target-domain configuration passes release gates. The application still works
without user training; accepted operational accuracy does not.

The new Jetson profile identifies the optimization order. Model forward,
preprocessing, and annotation/output account for approximately 95% of wall
time. Removing tracking or durable count storage would sacrifice solution
functionality while addressing less than 1% of the measured runtime.

## Remaining publication gates

1. Label representative roadside, truck, and/or sorting-line data under an
   approved governance and annotation protocol.
2. Freeze a target-domain test partition and report per-class detection and
   review performance.
3. Evaluate visible and unique counts on track-annotated video.
4. Optimize the Jetson model, preprocessing, and rendering path, then repeat
   the frozen condition and complete a multi-hour endurance run.
5. Obtain an independent clean-clone reproduction on another supported host.
6. Validate the maintained path on AMD hardware if AMD remains an advertised
   deployment target.
7. Measure operational outcomes before claiming route, worker, recovery, or
   cleanup benefit.

## Publication decision

Preprint 1.7 is a stronger systems and reproducibility paper because it
contains an accuracy signal, explicit prompts, class-confusion evidence, and a
replicated component profile. It remains unsuitable as a completed
production-efficacy paper. The low zero-shot result and sub-target Jetson
throughput are reported as findings, not hidden as limitations.
