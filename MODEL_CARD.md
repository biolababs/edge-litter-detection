# Model card: edge litter detector

## Model status

No trained release model exists yet. This card defines the information that
must be completed after data collection, training, and target-device evaluation.

## Implementation

- Primary implementation: RF-DETR Nano.
- Deployment formats under evaluation: PyTorch, ONNX, OpenVINO, TensorRT, and
  supported vendor artifacts.
- INT8 is considered only after representative calibration data is available.
- Confirmed target device: NVIDIA Jetson Orin Nano 8 GB Super, JetPack 6.2.3,
  L4T 36.5.2, in MAXN_SUPER mode.
- Deployment condition: coexistence with the device's existing LLM and
  application services.
- Additional portability target: compatible AMD ROCm/Strix Halo environment,
  with results reported separately.

## Intended use

Detect and classify visible litter items in camera images or video to support
research into urban cleanliness, environmental monitoring, and assisted waste
collection.

The application also reports the number of visible detections and the number of
confirmed track IDs encountered during the active run. Counting performance
must be validated separately from detection accuracy.

In a cleanup-truck workflow, the application may show a worker the predicted
class, confidence, and operator-configured separation stream. Uncertain items
must remain reviewable. A detection is not evidence that an item was physically
collected.

The system is decision support. It must not be used to identify, profile,
penalize, or track people.

## Out-of-scope use

- Facial recognition or person re-identification.
- Law-enforcement surveillance.
- Automated fines or enforcement actions.
- Hazardous-waste identification without a dedicated, validated dataset.
- Claims of material composition based solely on appearance.
- Safety-critical operation without human oversight and independent validation.
- Direct control of a hydraulic, pneumatic, or electric collection arm.

## Provisional classes

1. glass
2. metal
3. paper/cardboard
4. plastic
5. other litter

The final ontology must include written inclusion/exclusion rules and an
`unknown/ambiguous` annotation policy before labeling begins.

## Training data

Pending. Complete:

- source and license;
- capture dates and sites;
- camera and resolution;
- number of images and instances;
- class distribution;
- annotation quality process;
- de-identification method;
- site/session-level split method.

## Evaluation

Report at minimum:

- mAP50-95, mAP50, per-class AP;
- precision, recall, F1, and confusion matrix;
- performance by object size and environmental condition;
- Jetson end-to-end throughput and p50/p95 latency;
- GPU/CPU/RAM utilization, power mode, power draw, and temperature;
- sustained-run stability;
- visible-count error and unique-session count error on annotated video;
- duplicate-count and missed-count rates;
- accuracy retention and operational behavior for any quantized artifact.

## Known risks

- small, occluded, dirty, crushed, transparent, or reflective objects;
- class ambiguity from visual appearance;
- domain shift across cities, seasons, cameras, weather, and time of day;
- background and geographic bias;
- false positives from non-litter objects;
- privacy risk from bystanders and location metadata;
- thermal throttling or memory pressure on the edge device.
- interference with the existing shared-device workload.
- repeated counts after long occlusion, scene cuts, or fast camera motion;
- track merges when litter objects overlap.
- incorrect separation guidance when material cannot be determined visually;
- unsafe reliance on a detection when an independent controller, proximity
  sensor, or human safety check disagrees.

## Use-case release gate

Do not release the implementation until export compatibility, memory
headroom, accuracy, minority-class recall, sustained performance, data licenses,
privacy review, checksums, build environment, and limitations are documented.
The preferred incremental detector memory is at most 1.5 GiB; the hard initial
limit is 2.0 GiB while preserving at least 2.0 GiB available system memory.

