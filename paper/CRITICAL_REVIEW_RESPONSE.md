# Response to critical preprint review

Review incorporated: 21 October 2026
Manuscript revision: preprint 1.1

## Overall response

The review correctly identifies the manuscript as a software-systems and
reproducibility contribution whose principal scientific weakness is the absence
of representative detection and counting accuracy. The revision does not hide
that limitation. It strengthens the architecture description and preliminary
systems evidence while retaining accuracy, independent replication, and field
benefit as unresolved publication gates.

## Point-by-point disposition

| Review concern | Revision action | Status |
|---|---|---|
| No empirical accuracy evaluation | The introduction now explicitly identifies the contribution as software architecture rather than a new or accuracy-validated detector. A preliminary public-data evaluation remains required before stronger efficacy claims. | Open — critical |
| Thin repeated-image benchmarks | Added measured Jetson detector, complete 3,622-frame video, dashboard/API, memory, temperature, and whole-board power evidence. The manuscript still labels repeated-image T4/Jetson results narrowly and requires diverse-image repetitions and multi-hour endurance. | Partly addressed |
| Tracker insufficiently described | Added exact pseudocode, IoU threshold, mismatch penalty, greedy assignment, class voting, confirmation, expiry, and known absence of a motion/appearance model. | Addressed |
| Taxonomy asserted rather than justified | Added operational selection criteria, class group rationale, conservative TACO mapping rules, and a statement that frequency/confusability remain empirical questions. | Addressed at design level |
| No external validation | Added an explicit single-author validation limitation and an external clean-clone reproduction milestone. | Open |
| Narrow integrated-system related work | Added Litterati, TrashBot, and AMP Vision as examples of municipal/community measurement, smart disposal, and material-recovery product boundaries. | Addressed preliminarily |
| Paper too long for empirical content | The ResearchGate preprint retains reproducibility detail because it has no venue page limit. A shorter venue manuscript should move commands and operational detail to supplementary material after accuracy results exist. | Deferred for venue version |
| No inference-time energy discussion | Added Jetson whole-board power measurements and explained why detector-only energy per frame is withheld until power and run timestamps are synchronized. | Partly addressed |
| “Clean clone” undefined | Added a formal definition covering fresh checkout, no project environment/cache/private model/credential, and permitted public downloads. | Addressed |
| Demo mismatches unspecified | Added the source-label categories and concrete over-count, false-class, and missed-small-item examples. | Addressed |
| AI notice unusual | Added an editorial explanation that the notice discloses the AI-assisted document workflow and does not replace author verification or peer review. | Addressed subject to venue policy |

## Required empirical revision

The next publishable empirical increment should evaluate one frozen
configuration, not compare models:

1. Build and checksum a deterministic public-data bootstrap subset with
   source-group separation.
2. Record class support and exclude unsupported classes from macro summaries
   without concealing them.
3. Freeze prompts, thresholds, image size, model revision, and software commit.
4. Report COCO mAP50 and mAP50–95 plus per-class precision, recall, F1, support,
   and review rate.
5. Use track-annotated video for visible-count and unique-count error.
6. Obtain an independent clean-clone reproduction log.
7. Repeat the Jetson benchmark and complete a multi-hour endurance run after
   the optimized runtime is selected.

The public-data bootstrap result must be labeled as such. It cannot substitute
for representative truck, roadside, or sorting-line evaluation.

## Publication decision

Preprint 1.1 remains suitable as an openly labeled systems/reproducibility
technical preprint. It should not be submitted as a completed empirical
detection paper until the critical accuracy and counting evidence is added.

⚠️ AI & Data Notice: All output is AI-generated and must be independently
verified before sharing with customers or taking action.
