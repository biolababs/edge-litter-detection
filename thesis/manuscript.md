# Real-Time Litter Detection, Multiclass Classification, and Counting on an NVIDIA Jetson Orin 8 GB

Abiola A. Babsalaam  
Prospective MSc research revision  
20 October 2026

## Abstract

Litter in public spaces creates environmental, social, and economic costs, yet
manual inspection is difficult to sustain across large urban areas. This study
proposes an edge-computing system for detecting, classifying, tracking, and
counting visible litter with a compact object detector deployed on a confirmed
NVIDIA Jetson Orin Nano 8 GB Super device. The system uses RF-DETR Nano behind
a portable runtime adapter. The implementation must prove export and runtime
compatibility and will be evaluated on target-domain accuracy, minority-class
recall, count error, latency, throughput, memory, power, temperature, and
sustained stability. The model will be trained on a separate GPU environment
and evaluated on the Jetson through a supported deployment path.
The proposed class taxonomy contains glass, metal, paper/cardboard, plastic, and
other litter, subject to revision after a labeling pilot. Data will be split by
collection site and session to reduce leakage from near-duplicate video frames.
Privacy controls will exclude identity analysis and minimize the capture and
retention of identifiable people, vehicles, and locations. At the time of this
revision, new data collection, model training, and Jetson testing have not
been completed. Accordingly, this manuscript presents the research motivation,
design, reproducible methods, and analysis plan without claiming new accuracy
or real-time performance results.

## 1. Introduction

### 1.1 Background

Improperly discarded waste is a persistent feature of many built and natural
environments. Litter can obstruct drainage, reduce the usability and appearance
of public spaces, expose wildlife to ingestion or entanglement, and contribute
to the movement and fragmentation of plastic waste. Municipal responses
typically combine public education, collection infrastructure, scheduled
cleaning, and reports from residents or staff. These approaches remain
important, but they provide incomplete spatial and temporal visibility when
inspection is manual or intermittent.

Computer vision offers a complementary monitoring capability. A camera and
object-detection model can identify candidate litter, attach a class and
confidence score, and produce a structured event for review. Edge computing is
especially relevant because frames can be processed close to the camera,
reducing network dependency and allowing raw imagery to remain local. The
benefits are conditional: the model must be accurate enough for the intended
decision, the device must satisfy latency and power requirements, and the
camera workflow must protect privacy.

The author's 2023 project examined YOLOv7 training on AWS SageMaker and
deployment on a Raspberry Pi 4. That work established a useful problem
definition and produced historical training artifacts, but its publication
draft contained technical attribution errors, inconsistent metric
interpretations, non-portable notebook paths, an embedded API credential, and
an unsupported real-time performance claim. The current study therefore treats
the earlier work as motivation rather than validated evidence. It defines a new
experiment around a current detector and a more capable edge platform.

### 1.2 Proposed technology

The revised system is portable and targets a confirmed NVIDIA Jetson Orin
Nano Engineering Reference Developer Kit Super with 8 GB-class shared memory.
The device runs JetPack 6.2.3/L4T 36.5.2 and is shared with active application
and LLM services. RF-DETR Nano is the implementation model. The reusable
software separates RF-DETR inference from a standard detection schema,
tracking, class stabilization, and counting. The deployment is accepted only
if it can run with enough memory headroom for media processing, evidence
logging, the operating system, and the device's existing workload.

Training is performed off-device. The Jetson is reserved for export
validation, inference, and systems evaluation during an approved test window.
The existing project and its services will not be stopped or reconfigured for
this study.

### 1.3 Aim

The aim is to design and evaluate a reproducible, privacy-aware edge system for
multiclass litter detection, tracking, and counting on an NVIDIA Jetson Orin
8 GB device.

### 1.4 Objectives

1. Define an operational litter taxonomy and a documented annotation guide.
2. Assemble a licensed dataset containing public seed data and representative
   target-domain imagery.
3. Prevent train-test leakage by splitting data at site, session, or video
   sequence level.
4. Implement a portable detection schema and tracking-based counting pipeline.
5. Train RF-DETR Nano under controlled and reproducible conditions.
6. Export and validate the intended deployment artifact on the target Jetson.
7. Evaluate INT8 only after representative calibration data is available.
8. Measure accuracy, count error, latency, throughput, memory, power,
   temperature, and sustained-run stability.
9. Analyze detection and counting failures by class, object size, lighting,
   weather, occlusion, and scene type.
10. Publish reusable code, model documentation, citations, and—where licensing
    and privacy permit—data and trained artifacts.

### 1.5 Research questions

- RQ1: How accurately does the RF-DETR Nano implementation detect and classify
  litter on a held-out, target-representative test set?
- RQ2: Does the exported edge artifact preserve acceptable detection and
  classification accuracy?
- RQ3: Can the implementation meet the declared throughput, latency, memory,
  power, and thermal targets during sustained operation?
- RQ4: Which classes and environmental conditions account for the largest
  error rates?
- RQ5: How accurately can the system estimate visible objects and unique
  session counts without repeatedly counting the same item across frames?

### 1.6 Contributions

The intended contribution is not a new neural-network architecture. It is a
well-documented applied study that connects dataset governance, controlled
detector training, reusable hardware adapters, tracking-based counting, Jetson
optimization, systems benchmarking, privacy constraints, and honest
publication of limitations. The repository is designed so that the methods can
be inspected before results exist and the final claims can be traced to
machine-readable evidence.

## 2. Literature Review

### 2.1 Litter monitoring as an object-detection problem

Image classification assigns one or more labels to an image, whereas object
detection also estimates the location of each object. Location is necessary for
litter monitoring because a frame may contain several items, multiple material
classes, and substantial non-litter background. Detection output can support
counts, spatial overlays, confidence-based review, and error analysis at the
individual-object level.

Litter is a difficult visual category. Items may be small, partly covered,
crushed, wet, dirty, transparent, reflective, or visually similar to permanent
objects. A material label may be ambiguous from appearance alone. For example,
a reflective wrapper may resemble metal even when it is plastic, and a clear
container may not provide enough evidence to distinguish glass from plastic.
An annotation protocol should therefore permit an `other_litter` or ambiguous
outcome instead of forcing a material guess.

Prior litter datasets and studies demonstrate the feasibility of object
detection but also expose domain-shift risks. Internet or curated dataset
images may differ from the target camera in viewpoint, background, resolution,
weather, and object-size distribution. Reported benchmark accuracy is not a
substitute for evaluation on the intended deployment domain.

### 2.2 Evolution of real-time detection

One-stage detectors predict object classes and locations in a single model
pipeline and are widely used where latency matters. The YOLO family popularized
this approach and has evolved through changes in backbones, feature
aggregation, training strategies, heads, losses, and export paths. Comparison
between versions requires care because the name "YOLO" does not describe one
fixed architecture, implementation, license, or deployment behavior.

YOLOv7 was introduced by Wang, Bochkovskiy, and Liao in 2022. Its contribution
centered on trainable "bag-of-freebies" techniques, model scaling for
concatenation-based models, and training strategies including planned
re-parameterized convolution and auxiliary-head methods. It was not an
Ultralytics model and should not be described as a derivative of YOLOv6 with a
dual-stream attention head or Dice-loss replacement.

RF-DETR Nano is the selected implementation. RF-DETR is a real-time
detection-transformer family designed for fine-tuning, and its compact Nano
variant provides a practical starting point for portable edge deployment. Its
Jetson candidacy remains conditional on proving a supported export path and
stable execution on the exact target stack with acceptable memory use.

### 2.3 Edge AI and NVIDIA Jetson

Edge inference can reduce bandwidth, improve resilience during network
interruptions, and support local control of raw imagery. It also introduces
strict resource constraints. On an 8 GB Jetson, the model, CUDA context,
TensorRT engine, camera buffers, operating system, and application share
memory. Performance depends on power mode, clocks, cooling, JetPack, CUDA,
TensorRT, input resolution, precision, camera pipeline, and whether timing
includes preprocessing and postprocessing.

This makes systems evidence essential. A model-only benchmark can report a very
small inference time while a real camera application processes fewer frames
because decoding, copying, resizing, visualization, storage, and synchronization
add latency. The study will report pure inference, framework pipeline time, and
observed source-to-result throughput separately.

TensorRT supports optimized execution and lower-precision inference. FP16 is
the initial deployment baseline because it generally reduces memory and
improves throughput on supported Jetson hardware without requiring calibration.
INT8 requires representative calibration samples. Using unrelated or too few
calibration images can degrade accuracy, so INT8 export is intentionally
deferred until the final data distribution exists.

### 2.4 Role of a language or vision-language model

A conventional language model does not directly solve localized, frame-rate
object detection. A compact vision-language model can answer questions about
an image or produce a natural-language event summary, but it is more expensive
to run, less deterministic, and harder to evaluate for exhaustive bounding-box
detection.

For an 8 GB Jetson, the proposed optional role is asynchronous and selective.
The selected detector processes every frame. When a rule identifies an
important or uncertain event, a selected and de-identified frame could later be
sent to a compact local vision-language service for a human-readable summary.
The summary is auxiliary output and is never used as ground-truth annotation.
Because the target already hosts Ollama and llama-server processes, no
additional continuous VLM is included in the initial deployment.

### 2.5 Research gap

Many applied projects report accuracy without a frozen test protocol or call a
system "real time" using a model benchmark that omits the full pipeline. Others
do not record power mode, thermal state, data leakage controls, or privacy
handling. Counting studies may also sum frame detections and therefore count
one persistent object repeatedly. The revised study addresses these gaps by
specifying evidence before model training, separating target criteria from
observed results, and evaluating count error against track-level video ground
truth.

## 3. System Requirements and Architecture

### 3.1 Functional requirements

The system shall:

- accept images, recorded video, a camera index, or a supported stream;
- detect zero or more litter objects per frame;
- return class, confidence, and bounding-box information;
- assign stable track IDs where video continuity permits;
- report visible counts and unique confirmed-track counts by class;
- optionally save annotated media and structured JSON evidence;
- run through a replaceable model and accelerator adapter;
- continue detecting when the optional VLM is unavailable;
- retain version, configuration, and environment information for each reported
  run.

### 3.2 Non-functional requirements

The system shall:

- avoid hard-coded credentials and machine-specific absolute paths;
- use a fixed and documented class schema;
- expose confidence, IoU, image size, and maximum detections as configuration;
- produce repeatable benchmark artifacts;
- operate within the target device's memory and thermal limits;
- fail clearly when required models, data, or calibration inputs are absent;
- minimize retention of raw imagery and personally identifiable information.

### 3.3 Architecture

The runtime path is camera or media input, RF-DETR preprocessing, an
optimized detector runtime, standard detection records, class-stabilized
tracking, counting, and local event handling. It reports current visible
objects separately from unique confirmed track IDs encountered during the
session. Evidence is written as streaming JSON Lines plus an end-of-run
summary. A selected-frame VLM, if enabled later, is downstream and asynchronous.

Training occurs on a GPU host using versioned configuration and data. The best
checkpoint is transferred to the target deployment environment. The export
manifest records the source weights, format, precision, image size, software
versions, and calibration data where applicable. Each CPU, NVIDIA, AMD, or
Jetson deployment retains its own manifest; evidence from one device is not
generalized to another.

### 3.4 Implementation acceptance

RF-DETR Nano is accepted for the use case only if it exports to a supported
edge runtime, loads with sufficient memory headroom, completes representative
media without unsupported operators or crashes, and meets the frozen detection,
classification, and counting accuracy requirements.

The preferred detector incremental memory is at most 1.5 GiB. The deployment
fails the initial gate if it exceeds 2.0 GiB incremental memory, leaves less
than 2.0 GiB available for the existing workload, depends on swapping, or shows
sustained memory growth.

The initial image size is 640 pixels. A lower-resolution deployment setting may
be tested if necessary to meet the operational target, but its detection and
counting accuracy must be re-evaluated before use.

## 4. Methodology

### 4.1 Research design

The study is an empirical design-and-evaluation project. It combines controlled
model development with measurement of an implemented edge system. Threshold
selection will use validation data; the held-out test set will be used only
after training and threshold choices are frozen.

### 4.2 Data acquisition

The dataset will combine licensed public litter imagery with target-domain
camera data. A source inventory will record dataset version, license,
attribution, image count, annotation format, download date, and redistribution
restrictions.

Target-domain collection will sample relevant scene types, times of day,
weather, backgrounds, camera heights, object sizes, occlusion, and material
conditions. Collection should be planned rather than opportunistic so the test
set represents the use case. Images containing identifiable people, license
plates, home addresses, or unnecessary precise location metadata will be
excluded or de-identified according to the approved protocol.

### 4.3 Class ontology

The provisional classes are glass, metal, paper/cardboard, plastic, and other
litter. A pilot will test whether annotators can apply these classes
consistently. If material cannot be reliably inferred, the ontology will be
revised before large-scale labeling. Every change will increment the dataset
schema version.

The annotation guide will define:

- the minimum visible evidence for each class;
- how to label overlapping and partly occluded objects;
- when several pieces form one object or multiple objects;
- minimum box size and truncation rules;
- treatment of bins, leaves, permanent signs, and non-litter background;
- an ambiguous/exclusion process.

### 4.4 Annotation quality

A pilot subset will be labeled by at least two annotators where feasible.
Disagreement will be reviewed to refine the guide. Automated validation will
check class IDs, coordinates, empty or corrupt files, duplicate images, and
boxes outside image boundaries. Class and object-size distributions will be
reported before training.

### 4.5 Data splitting and leakage prevention

Adjacent video frames and repeated views of the same scene are highly
correlated. Random image-level splitting can place nearly identical content in
training and test sets and inflate performance. The data will therefore be
grouped by collection site, session, or source video before assignment to
training, validation, and test partitions.

A provisional 70/15/15 group split will be used, subject to adjustment for
class coverage. Augmentation is applied only after splitting. The test
partition will be frozen and checksummed before final accuracy evaluation.

### 4.6 Training

RF-DETR Nano will begin from official pretrained weights. The dataset version,
augmentations, optimization settings, and resolved batch size will be retained
in the run artifacts.

Each run will preserve its framework arguments, training curves, validation
metrics, package versions, Git revision, and best checkpoint. If compute
permits, at least three seeds will be trained so the reported accuracy does not
rely on one random initialization and data order.

Hyperparameter tuning, if performed, will use validation data only. The scope
and search budget will be disclosed. The test set will not be used to select
epochs, augmentations, image size, confidence threshold, or model size.

### 4.7 Model export

The frozen checkpoint will be transferred to the target Jetson only after the
read-only hardware inventory and export feasibility review. A supported
artifact will be built with a fixed input shape.
The source checkpoint and deployment artifact will each have a checksum and
manifest. Construction will be repeated after material changes to JetPack,
CUDA, TensorRT, or target module.

INT8 will be evaluated only after a representative calibration subset is
frozen. Calibration data will come from the training distribution, not the
held-out test set. INT8 accuracy will be re-evaluated using the same test set
and thresholds appropriate to that exported model.

### 4.8 Jetson test controls

The read-only inventory confirmed a Jetson Orin Nano Engineering Reference
Developer Kit Super, Ubuntu 22.04.5, kernel 5.15.199-tegra, JetPack 6.2.3,
L4T 36.5.2, TensorRT Python 10.3.0, Python 3.10.12, and MAXN_SUPER power mode.
The snapshot showed 7.4 GiB total physical memory, 4.5 GiB available memory,
approximately 772 GiB available on the root NVMe filesystem, and no attached
`/dev/video*` camera. The system Python did not contain PyTorch or RF-DETR. No
software was installed and no service or configuration was changed.

The device is shared with active local LLM inference, application, and
development services. Initial tests will therefore use recorded video and an
isolated, version-pinned runtime only after explicit authorization. They will
not alter the system Python, occupy an existing service port, stop the current
workload, or treat swap as usable real-time inference capacity.

The hardware model, carrier board, storage, camera, power supply, cooling,
JetPack, CUDA, TensorRT, Python, framework versions, power mode, and clock
policy will be recorded again for each validation run. The power mode and
coexistence condition will remain fixed within the reported result. Clock-lock
status remains pending because the read-only
inventory user could not run the root-required `jetson_clocks --show` command.

Each condition will include warm-up followed by repeated measurement. A
`tegrastats` log will run alongside the benchmark. The system will be tested
for a sustained period to detect thermal throttling, memory growth, camera
failures, or performance drift.

### 4.9 Evaluation metrics

Detection evaluation will include mAP50-95, mAP50, per-class AP, precision,
recall, F1, confusion matrix, and errors stratified by object size and scene
condition. The operating confidence threshold will be chosen using validation
data and then frozen.

Counting evaluation will use videos with track-level ground truth. It will
report per-frame count error, mean absolute count error, unique-session count
error, duplicate-track rate, missed-track rate, and class reassignment within a
track. Results will be stratified by camera motion, occlusion, object density,
and scene cuts. Detection mAP will not be treated as proof of count accuracy.

The implementation provides a held-out RF-DETR evaluation command and a
separate aggregate count evaluator. The latter consumes runtime JSON Lines
events and annotated visible/session counts. Duplicate-track, missed-track,
and identity-switch rates will be computed only when persistent ground-truth
object identities are available; aggregate counts alone cannot support those
claims.

Systems evaluation will include:

- model inference latency;
- preprocessing, inference, and postprocessing latency;
- observed source-to-result frames per second;
- p50 and p95 latency;
- memory use;
- power and energy per frame where feasible;
- temperature and clock state;
- first-inference latency;
- sustained-run reliability.

The provisional real-time engineering target is at least 15 processed frames
per second without sustained thermal throttling. This target may be revised
before tests, but it must not be reported as an achieved result until measured.

### 4.10 Statistical analysis

Principal Jetson conditions will be repeated at least three times. Results will
include mean, median, p95, range, and run-to-run variability. Where the test set
is large enough, bootstrap confidence intervals will be used for key accuracy
metrics. Per-class results will be interpreted with their support counts;
strong aggregate performance will not conceal a weak minority class.

### 4.11 Error analysis

False positives and false negatives will be sampled across classes and
conditions. The analysis will distinguish annotation ambiguity, insufficient
resolution, occlusion, domain shift, class confusion, background confusion, and
threshold effects. Proposed improvements will be tied to observed error modes
rather than assumed causes.

## 5. Ethics, Privacy, Security, and Sustainability

### 5.1 Privacy

The system detects litter, not people. Person identification, face recognition,
license-plate recognition, behavior scoring, and automated enforcement are out
of scope. Camera placement should minimize capture of private property and
bystanders. Raw video retention should be minimized, access controlled, and
separated from published research artifacts.

Where public-space recording requires notice, permission, ethics approval, or a
data-protection assessment, collection will not begin until that requirement is
met. Published samples will be manually reviewed for identity and location
risk.

### 5.2 Bias and limitations

Performance may vary across locations, socioeconomic contexts, seasons,
weather, camera quality, and cleaning practices. A class taxonomy based on
material appearance may be less reliable for dirty, transparent, composite, or
damaged objects. The manuscript will report these limitations and will not
generalize from one city or camera to all urban environments.

### 5.3 Security

Credentials will be supplied through environment variables or an excluded
secret store. The historical hard-coded Roboflow credential must be revoked.
Model checkpoints will be downloaded from official sources, checksummed, and
treated as executable-like artifacts. The Jetson should use least-privilege
services, restricted inbound access, and regular supported software updates
outside a frozen experiment period.

### 5.4 Sustainability

Edge processing avoids continuous transmission of raw video but still consumes
energy and hardware. The study will report power and energy-per-frame evidence
where feasible. The selected RF-DETR Nano implementation will be kept only as
large as required by the use-case accuracy target. Data and model retraining
will be versioned to avoid unnecessary repeated experiments.

## 6. Results: Pending Data and Testing

No new dataset, training run, TensorRT engine, or Jetson benchmark has been
completed for this revised study. A read-only hardware inventory has been
completed; it is environmental evidence, not a model-performance result. The
remaining tables are templates and must not be read as results.

### 6.1 Confirmed target environment

| Item | Observed value |
|---|---|
| Device | Jetson Orin Nano Engineering Reference Developer Kit Super |
| JetPack / L4T | 6.2.3 / 36.5.2 |
| Operating system | Ubuntu 22.04.5 LTS |
| Power mode | MAXN_SUPER |
| Physical memory at capture | 7.4 GiB total; 4.5 GiB available |
| TensorRT / Python | TensorRT 10.3.0 package; Python 3.10.12 |
| Current workload | Ollama, llama-server, Node, Python, and OpenCode services observed |
| Camera | none observed |
| Inventory effect | read-only; no device changes |

### 6.2 Dataset summary

| Item | Value |
|---|---|
| Dataset version | pending |
| Public sources and licenses | pending |
| Target-domain collection sites/sessions | pending |
| Training images / instances | pending |
| Validation images / instances | pending |
| Test images / instances | pending |
| Class distribution | pending |
| Annotation agreement | pending |

### 6.3 Accuracy results

| Model | Precision | Recall | F1 | mAP50 | mAP50-95 |
|---|---:|---:|---:|---:|---:|
| RF-DETR Nano litter model | pending | pending | pending | pending | pending |

### 6.4 Counting results

| Model / tracker | Frame-count MAE | Unique-count error | Duplicate-track rate | Missed-track rate |
|---|---:|---:|---:|---:|
| RF-DETR Nano + class-stabilized IoU | pending | pending | pending | pending |

### 6.5 Jetson performance

| Model | Power mode | FPS | p50 latency | p95 latency | RAM | Power | Peak temperature |
|---|---|---:|---:|---:|---:|---:|---:|
| RF-DETR Nano deployed artifact | MAXN_SUPER | pending | pending | pending | pending | pending | pending |

### 6.6 Error analysis

Complete after testing:

- most frequent false-positive class and scene;
- most frequent false-negative class and object size;
- performance under low light and wet conditions;
- transparent/reflective material confusion;
- effect of occlusion and clutter;
- duplicate and missed counts after occlusion or camera motion;
- track merges and class changes;
- annotation ambiguity discovered during review.

## 7. Discussion: Pending Results

This chapter will interpret measured results against the research questions and
the declared system targets. It will assess RF-DETR detection, classification,
tracking, counting, and full-pipeline operation and explain failure modes. It
will not infer scalability, city-wide impact, cost-effectiveness, or
environmental benefit solely from laboratory detection metrics.

## 8. Conclusion and Planned Work

This manuscript defines a technically corrected and reproducible plan for
multiclass litter detection and counting on a confirmed Jetson Orin Nano 8 GB
Super device. RF-DETR Nano is the implementation model; model-family comparison
is out of scope. The design integrates a portable runtime adapter,
class-stabilized tracking, use-case acceptance gates, dataset leakage controls,
annotation quality, hardware manifests, full-pipeline validation, privacy,
security, and publication requirements.

The next work is empirical: approve the data protocol, collect and label data,
train RF-DETR Nano, obtain an authorized Jetson test window, export a supported
artifact, run the accuracy and operational validation, and populate the Results
and Discussion chapters. Until that work is complete, the project should be
described as a research design and implementation scaffold rather than a
validated real-time system.

## References

Amazon Web Services. (n.d.). Amazon SageMaker documentation.
https://docs.aws.amazon.com/sagemaker/

Jambeck, J. R., Geyer, R., Wilcox, C., Siegler, T. R., Perryman, M., Andrady,
A., Narayan, R., & Law, K. L. (2015). Plastic waste inputs from land into the
ocean. Science, 347(6223), 768–771.
https://doi.org/10.1126/science.1260352

Kaza, S., Yao, L. C., Bhada-Tata, P., & Van Woerden, F. (2018). What a Waste
2.0: A Global Snapshot of Solid Waste Management to 2050. World Bank.
https://doi.org/10.1596/978-1-4648-1329-0

NVIDIA. (2026). JetPack SDK. https://developer.nvidia.com/embedded/jetpack

NVIDIA. (n.d.). Jetson Orin Nano Super Developer Kit.
https://www.nvidia.com/en-us/autonomous-machines/embedded-systems/jetson-orin/nano-super-developer-kit/

Redmon, J., Divvala, S., Girshick, R., & Farhadi, A. (2016). You Only Look
Once: Unified, Real-Time Object Detection. Proceedings of the IEEE Conference
on Computer Vision and Pattern Recognition, 779–788.
https://doi.org/10.1109/CVPR.2016.91

Roboflow. (2026). RF-DETR.
https://github.com/roboflow/rf-detr

Roboflow. (2026). RF-DETR export documentation.
https://rfdetr.roboflow.com/latest/learn/export/

Wang, C.-Y., Bochkovskiy, A., & Liao, H.-Y. M. (2022). YOLOv7: Trainable
bag-of-freebies sets new state-of-the-art for real-time object detectors.
arXiv:2207.02696. https://doi.org/10.48550/arXiv.2207.02696

## Appendix A. Reproduction commands

Training:

`python train.py --data data/litter --model rfdetr-nano`

Portable ONNX export:

`python export_model.py --weights runs/litter/rfdetr-nano-baseline/checkpoint_best_ema.pth --format onnx --precision fp32`

Inference:

`python infer.py --model models/rfdetr-nano-litter.pth --source 0 --max-frames 1000`

Benchmark:

`python benchmark.py --model models/rfdetr-nano-litter.pth --source data/litter/images/test --output reports/generated/jetson-rfdetr.json`

## Appendix B. Completion gate

- Preserve the dated Jetson inventory and recapture it before benchmarking.
- Revoke historical API credential.
- Approve ethics and privacy plan.
- Obtain an authorized Jetson test window without disrupting the existing
  project.
- Freeze class guide, data version, and held-out split.
- Train and freeze the RF-DETR Nano litter checkpoint.
- Complete export, accuracy, counting, and memory acceptance gates.
- Export the supported artifact and conditionally evaluate INT8.
- Capture accuracy, count error, latency, throughput, memory, power, and
  temperature.
- Replace pending tables with traceable evidence.
- Independently verify citations and claims.
- Select licenses and publish code, data, weights, and manuscript only within
  their permitted scopes.

## AI and data notice

⚠️ AI & Data Notice: All output is AI-generated and must be independently
verified before sharing with customers or taking action.

