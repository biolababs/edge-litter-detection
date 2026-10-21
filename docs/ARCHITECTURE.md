# System architecture

## Decision

Use a portable application core with one project-maintained RF-DETR Nano
checkpoint as the selected release detector. Users download the versioned,
checksum-verified artifact; they do not train it.

Grounding DINO Tiny remains the default functional bootstrap. OmDet-Turbo Tiny
is an integrated no-training acceptance candidate with confidence-scored
open-vocabulary output. This is one litter solution with bootstrap and release
paths, not a model leaderboard.

## Components

1. **Capture**
   - Attached camera, image, downloaded video, or live stream.
   - Source identifiers are sanitized before evidence is written.

2. **Detection and classification**
   - RF-DETR Nano is the selected fixed-taxonomy release detector.
   - Grounding DINO Tiny is the default functional bootstrap.
   - OmDet-Turbo Tiny is the no-training acceptance candidate.
   - Stable class IDs and names come from `config/classes.yaml`.
   - Adapters normalize output into the common `Detection` schema.

3. **Duplicate suppression**
   - Class-agnostic non-maximum suppression reduces overlapping boxes caused by
     semantically overlapping prompts.

4. **Tracking and counting**
   - Class-stabilized IoU tracking associates detections across frames.
   - Visible objects and confirmed unique run tracks are counted separately.

5. **Human-assisted separation**
   - `config/separation.yaml` maps classes to operator-defined destinations.
   - Low-confidence, hazardous, and ambiguous items enter the review queue.

6. **Evidence and persistence**
   - Streaming JSON Lines and end-of-run JSON summaries.
   - Optional annotated media.
   - SQLite runs, frame observations, aggregate counts, review records,
     collection confirmations, and durable integration events.

7. **External integration**
   - A fleet connector can read the outbox during or after a route.
   - A human, controller, or sensor-fusion service separately confirms a pickup.
   - Detection never proves collection.

## Runtime flow

```text
image / video / camera / stream
                |
                v
      bootstrap/release adapter
                |
                v
      standard Detection records
                |
                v
     duplicate suppression + tracking
                |
                v
     visible + unique run counts
        /          |          |           \
     JSONL    JSON summary   SQLite    annotated media
                                |
                    review queue + outbox/API
```

## Deployment constraints

- The reference core is portable across CPU, NVIDIA CUDA, AMD ROCm, and Jetson.
- Each target receives its own benchmark and environment manifest.
- The shared Jetson must not be modified outside an authorized maintenance
  window.
- Existing LLM and application services remain untouched.
- Mechanical actuation stays outside this process and under a safety-rated
  controller.

The thesis Jetson currently has a preferred incremental detector memory target
of 1.5 GiB, a hard initial limit of 2.0 GiB, and a requirement to preserve at
least 2.0 GiB available memory during coexistence testing. These are acceptance
targets, not measured results.

## Failure behavior

- Missing model runtime, configuration, or source: fail clearly.
- First model download unavailable: retain no false success state and
  report the connection/cache error.
- Camera disconnect: record failure and allow a process supervisor to restart.
- Low-confidence or ambiguous object: preserve it for review.
- Scene cut or tracking loss: retain frame detections and disclose possible
  duplicate run counts.
- SQLite/fleet connection unavailable: keep local outbox records for retry.
- Safety input unavailable or contradictory: external arm control remains
  inhibited.
