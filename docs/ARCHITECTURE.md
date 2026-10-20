# System architecture

## Decision

Use a portable application core with RF-DETR Nano as the detector. Train it on
a separate GPU host and deploy the validated artifact through a
hardware-specific runtime adapter. Model-family comparison is out of scope.

A detector is a better fit than an LLM for the real-time path because the task
requires localized bounding boxes, repeatable confidence scores, and measurable
latency. A compact vision-language model may later summarize selected events,
but it must not replace detector evaluation.

## Components

1. **Capture**
   - CSI or USB camera, image directory, video, or RTSP source.
   - Timestamp and capture-session identifier.

2. **Preprocessing**
   - Resize/letterbox to the configured image size.
   - Apply RF-DETR's versioned normalization and tensor layout.

3. **Detection**
   - RF-DETR PyTorch is the primary executable adapter.
   - PyTorch, ONNX, OpenVINO, TensorRT, or a supported vendor runtime.
   - Confidence and IoU thresholds are versioned in `config/project.yaml`.

4. **Tracking and counting**
   - Associate detections across frames using class-stabilized IoU tracking.
   - Report current visible counts and confirmed visible counts.
   - Count a confirmed track once per process session.
   - Keep the counting implementation independent of the model runtime.

5. **Event handling**
   - Detection class, confidence, box, frame identifier, and timing.
   - Streaming JSON Lines, an end-of-run summary, and optional annotated media.
   - No face or identity analytics.

6. **Evidence**
   - JSON run manifest.
   - Environment and software versions.
   - Benchmark timing.
   - Separate `tegrastats` capture for power, memory, and thermals.

7. **Optional VLM**
   - Triggered only for selected frames or offline review.
   - Receives a de-identified image plus detector output.
   - Produces natural-language summaries that are never treated as ground truth.
   - Disabled for the initial deployment because the shared Jetson already
     hosts LLM services.

## Confirmed deployment constraints

- Jetson Orin Nano 8 GB Super, JetPack 6.2.3, L4T 36.5.2.
- Existing Ollama/llama-server and application services remain untouched.
- Detector incremental memory target: at most 1.5 GiB preferred, 2.0 GiB hard
  initial limit.
- Preserve at least 2.0 GiB available memory during coexistence testing.
- No camera was present during inventory, so use recorded video for the first
  smoke test.
- Training remains off-device.

These constraints describe the thesis Jetson. CPU, NVIDIA CUDA workstation, AMD
ROCm/Strix Halo, and other edge-device runs receive separate environment and
benchmark manifests.

## Deployment boundary

The application depends on the standard `Detection` schema, not a framework
object. Hardware-specific adapters convert model output into that schema.
TensorRT engines remain platform-specific and must be produced for a compatible
target stack. Keep original checkpoints and export manifests so all deployment
artifacts are traceable.

## Failure behavior

- Missing model/config/source: fail with a clear error.
- Camera disconnect: record the failure and restart under a service manager.
- Thermal throttling: flag the benchmark as invalid unless temperature and
  clock behavior are recorded.
- Low-confidence or ambiguous object: retain as an uncertain detection; do not
  force a material classification.
- Tracking failure or scene cut: retain frame detections and flag the session
  count as potentially duplicated.
- VLM unavailable: continue detection without it.

