# Research preprint package

This directory contains the publication package for the Edge Litter Detection
software.

## Files

- `edge_litter_detection_preprint.md`: editable source manuscript;
- `Edge_Litter_Detection_Preprint.docx`: formatted editable manuscript;
- `Edge_Litter_Detection_Preprint.pdf`: upload-ready preprint;
- `RESEARCHGATE_SUBMISSION.md`: title, abstract, keywords, rights checks, and
  upload checklist;
- `evidence/preliminary_validation.json`: machine-readable evidence boundary;
- `evidence/t4_omdet_preliminary.json`: transcribed Tesla T4 benchmark record.

## Publication status

This is a systems and reproducibility preprint. It reports verified software
functionality and preliminary engineering measurements. Target-domain
detection accuracy, video counting accuracy, Jetson and AMD sustained
performance, power, thermals, and field outcomes remain pending.

Do not describe the manuscript as peer reviewed unless it is later accepted by
a peer-reviewed venue. Before upload, the author should independently verify
all claims and references, inspect the generated PDF, and select the desired
manuscript license.

## Software cited

The paper references Edge Litter Detection version 0.10.1 at Git commit:

`0624677b72cf1d16b59a335b78d9003f2b479786`

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
