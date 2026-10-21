# Counting semantics

## Outputs

The application reports three distinct quantities:

- `visible_counts`: detections visible in the current frame;
- `confirmed_visible_counts`: currently visible objects whose tracks have met
  the confirmation threshold;
- `unique_session_counts`: confirmed track IDs seen at least once during the
  current process run.

These values answer different questions. A dashboard that needs "how much
litter is visible now" should use `visible_counts`. A moving-camera inspection
that needs "how many items were encountered during this run" should use
`unique_session_counts`.

## Avoiding repeated counts

Video contains the same object in many frames. Summing frame detections would
greatly overcount litter. The built-in tracker associates boxes across frames
using overlap, retains tracks through short detection gaps, and uses class votes
to reduce label flicker. A track is added to the unique count only after it has
appeared in the configured number of frames.

Default controls:

| Setting | Default | Purpose |
|---|---:|---|
| IoU threshold | 0.30 | Minimum box overlap for association |
| Minimum confirmed hits | 2 | Suppress one-frame false detections |
| Maximum missed frames | 30 | Preserve identity through a short gap |
| Class mismatch penalty | 0.75 | Prefer class-consistent matches without forcing them |

## Important limitation

The built-in tracker is intentionally small and dependency-free. It is a strong
starting point for fixed or slowly moving cameras and mostly stationary litter.
It is not a universal identity system. Fast camera motion, long occlusion,
crowded overlapping items, scene cuts, and looped video can create a new track
for an already seen object.

For a production moving-camera deployment, evaluate the built-in tracker
against ByteTrack, BoT-SORT, or a geospatial deduplication method using the same
frozen video. The selected method and error rate must be reported with the
count; object-detection accuracy alone does not validate counting accuracy.

## Persistence

Unique counts remain session-scoped, but they are persisted automatically to
`state/litter-edge.db` with the run ID, edge-device ID, vehicle ID, route ID,
and timestamps. Restarting the process creates a new run rather than erasing
previous records.

Use `python query_counts.py summary` to inspect persisted totals. Summing unique
counts across runs can still count the same physical item twice; route-level or
geospatial deduplication remains an integration responsibility.

The database stores externally confirmed pickups separately from model
observations. A detection or unique track must never be reported as collected
unless a human, arm controller, sensor-fusion component, or reviewed import
submits a collection confirmation.
