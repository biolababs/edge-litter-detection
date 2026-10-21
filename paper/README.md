# Research preprint package

This directory contains the publication package for the Edge Litter Detection
software.

## Files

- `edge_litter_detection_preprint.md`: editable source manuscript;
- `Edge_Litter_Detection_Preprint.docx`: formatted editable manuscript;
- `Edge_Litter_Detection_Preprint.pdf`: upload-ready preprint;
- `RESEARCHGATE_SUBMISSION.md`: title, abstract, keywords, rights checks, and
  upload checklist;
- `SUPPLEMENTARY_REPRODUCIBILITY.md`: exact demonstration, evaluation,
  profiling, and validation commands moved out of the manuscript;
- `CRITICAL_REVIEW_RESPONSE.md`: point-by-point disposition of the major
  preprint review;
- `evidence/preliminary_validation.json`: machine-readable evidence boundary;
- `evidence/t4_omdet_preliminary.json`: transcribed Tesla T4 benchmark record;
- `evidence/jetson_orin_nano_validation.json`: Jetson protocol, measured
  outcomes, checksums, acceptance interpretation, and limitations;
- `evidence/jetson_orin_nano_omdet_benchmark.json`: raw Jetson benchmark output;
- `evidence/jetson_orin_nano_video_smoke_summary.json`: complete video run
  summary; and
- `evidence/jetson_orin_nano_full_video_summary.json`: 3,622-frame full-file
  stability summary;
- `evidence/jetson_profile_warm_aggregate.json`: three-run warmed Jetson
  component profile, runtime versions, telemetry summary, and checksums;
- `evidence/jetson_profile_warm_run_*.json`: raw warmed full-pipeline profile
  summaries;
- `evidence/jetson_profile_warm_tegrastats.log`: raw three-run device
  telemetry;
- `evidence/taco_omdet_zero_shot_accuracy.json`: grouped public-data accuracy
  result and evidence boundary; and
- `evidence/taco_omdet_zero_shot_predictions.json`: COCO-format model
  predictions used for the reported evaluation.

## Publication status

This is a systems and reproducibility preprint. It reports verified software
functionality, a preliminary grouped TACO zero-shot evaluation, and constrained
Jetson Orin Nano coexistence validation. The public checkpoint measured
0.0765 mAP50–95 and 0.0749 micro F1, so it is a software bootstrap rather than
a production-accepted litter model. Three warmed full-pipeline Jetson runs
averaged 5.1877 FPS and did not meet the provisional 15 FPS target.
Target-domain accuracy, video counting accuracy, multi-hour Jetson acceptance,
AMD performance, and field outcomes remain pending.

Do not describe the manuscript as peer reviewed unless it is later accepted by
a peer-reviewed venue. Before upload, the author should independently verify
all claims and references, inspect the generated PDF, and select the desired
manuscript license.

## Software cited

The paper references Edge Litter Detection version 0.11.0. The principal
warmed Jetson profile was executed at Git commit:

`618954e5921305addbd147ccc96ea1d78fe34c6e`

The grouped TACO evaluation was executed at:

`142eecf470a91d7d270b89ecdd6d3037b5a90809`

Repository:

`https://github.com/biolababs/edge-litter-detection`

## Regenerating the document

The DOCX input is generated from the Markdown source and then rendered with the
document-generation workflow. The PDF is exported from the resulting DOCX.
Generated artifacts should be reviewed after every substantive manuscript
change.

## Notice

⚠️ AI & Data Notice: All output is AI-generated and must be independently
verified before sharing with customers or taking action.
