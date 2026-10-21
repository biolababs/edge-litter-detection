# Research preprint package

This directory contains the publication package for the Edge Litter Detection
software.

## Files

- `edge_litter_detection_preprint.md`: editable source manuscript;
- `Edge_Litter_Detection_Preprint.docx`: formatted editable manuscript;
- `Edge_Litter_Detection_Preprint.pdf`: upload-ready preprint;
- `RESEARCHGATE_SUBMISSION.md`: title, abstract, keywords, rights checks, and
  upload checklist;
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
- `evidence/jetson_orin_nano_*_tegrastats.log`: raw device telemetry.

## Publication status

This is a systems and reproducibility preprint. It reports verified software
functionality, preliminary engineering measurements, and one constrained
Jetson Orin Nano coexistence validation. Target-domain detection accuracy,
video counting accuracy, repeated/multi-hour Jetson acceptance, AMD
performance, and field outcomes remain pending. The measured Jetson path is
functional but did not meet the provisional 15 FPS target.

Do not describe the manuscript as peer reviewed unless it is later accepted by
a peer-reviewed venue. Before upload, the author should independently verify
all claims and references, inspect the generated PDF, and select the desired
manuscript license.

## Software cited

The paper references Edge Litter Detection version 0.10.1 at Git commit:

`756fa2ae0b8686bb4b97940911710dc73f8efd90`

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
