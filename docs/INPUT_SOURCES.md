# Input sources

The same runtime accepts local images, downloaded videos, attached cameras,
and live streams. Source probing does not load the model.

## One-command startup

```bash
./startup.sh
```

With no source argument, the launcher:

1. checks attached camera indexes;
2. selects the first camera that returns a frame;
3. otherwise selects the first supported file under `media/`;
4. otherwise asks for an image path, video path, camera index, or stream URL.

Pass a source directly for unattended startup:

```bash
./startup.sh --source 0
./startup.sh --source ./media/litter.jpg
./startup.sh --source ./media/litter.mp4
./startup.sh --source "$LITTER_STREAM_URL" --no-display
```

Operate the same source types from the browser:

```bash
./startup.sh --dashboard --backend omdet_turbo
```

The dashboard is served at `http://127.0.0.1:8088`. It starts a server-side
capture session, so camera indexes and local paths refer to the edge device
rather than the operator's browser computer.

Download an attributed recycling-facility conveyor video:

```bash
python prepare_demo_video.py --format path
```

Or download it and run the command-line pipeline automatically:

```bash
./startup.sh --backend omdet_turbo --demo-video --no-display
```

The downloaded `media/demo-video/recycling-facility.webm` sample shows mixed
recyclables moving through a material-recovery facility. Its creator, source,
CC BY-SA 3.0 license, permission status, and checksums are retained in the
adjacent generated manifest. It is functional stream media rather than a
labelled accuracy dataset.

## Discover and probe

List attached cameras:

```bash
python discover_sources.py --list-cameras
```

Probe one source:

```bash
python discover_sources.py --source VALUE
```

The JSON result reports whether the source opened, whether a frame was read,
frame dimensions, reported frame rate, and the OpenCV capture backend.

## Source types

| Source | Example | Notes |
|---|---|---|
| Image | `./media/site.jpg` | JPEG, PNG, BMP, TIFF, and WebP |
| Video | `./media/site.mp4` or `.webm` | Codec support depends on OpenCV/FFmpeg |
| Camera | `0` | Camera indexes normally start at zero |
| RTSP stream | `rtsp://camera-host/live` | Prefer an environment variable for credentials |
| HTTP stream | `https://camera-host/stream` | Must be supported by the OpenCV build |

Downloaded images and videos are ordinary local file paths; no special import
step is required.

## Camera permissions

- macOS may ask for Terminal or the launching application to receive camera
  permission.
- Linux camera users normally need access to `/dev/video*`.
- A container requires the camera device to be explicitly passed through.
- A headless system should use `--no-display`.

## Stream credentials

The runtime removes usernames, passwords, and query strings from JSON evidence
and error messages. Credentials can still appear in shell history if entered
directly. Prefer:

```bash
export LITTER_STREAM_URL="rtsp://user:password@camera-host/live"
./startup.sh --source "$LITTER_STREAM_URL" --no-display
```

Do not store stream credentials in Git-tracked configuration.

## Live-source behavior

Use `Ctrl+C` for a controlled stop. A service deployment should run the
application under systemd, Docker, or another supervisor so a disconnected
camera or stream can be restarted according to the site's policy.

Dashboard stream-control endpoints:

```text
POST   /v1/streams
GET    /v1/streams
GET    /v1/streams/{session_id}
GET    /v1/streams/{session_id}/frame.jpg
DELETE /v1/streams/{session_id}
```

The default limit is one active stream because accelerator memory and model
execution are shared. The stream URL is retained only in process memory; API,
SQLite, and UI representations remove user information and query strings.
