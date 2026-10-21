# Event output contract

The streaming CLI writes one JSON object per processed frame to the configured
JSON Lines file. The machine-readable contract is
`schemas/detection-event.schema.json`.

Example:

```json
{
  "run_id": "03d55ad2-9b06-4ef3-a137-755017799213",
  "source": "camera-01.mp4",
  "edge_device_id": "edge-truck-01",
  "vehicle_id": "truck-12",
  "route_id": "route-a",
  "frame_index": 42,
  "timestamp_seconds": 1.4,
  "inference_ms": 31.2,
  "visible_counts": {
    "plastic": 2
  },
  "confirmed_visible_counts": {
    "plastic": 2
  },
  "unique_session_counts": {
    "plastic": 3
  },
  "newly_confirmed_track_ids": [
    7
  ],
  "detections": [
    {
      "bbox_xyxy": [
        100.0,
        90.0,
        180.0,
        210.0
      ],
      "confidence": 0.91,
      "class_id": 3,
      "class_name": "plastic",
      "track_id": 7,
      "confirmed": true,
      "separation_destination": "plastic_stream",
      "review_required": false
    }
  ]
}
```

Stream credentials and query parameters are removed from `source`. Consumers
must treat `run_id` as the unique session boundary. Unique counts from different
runs must not be added without an application-specific deduplication policy.
The vehicle, route, and edge-device fields allow downstream fleet systems to
partition observations without deriving identity from private hostnames.

`separation_destination` is operator-configured guidance. It is not an actuator
command, and `review_required` tells a human-assistance interface to request a
confirmation or correction.
