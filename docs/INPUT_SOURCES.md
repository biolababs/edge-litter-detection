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
| Video | `./media/site.mp4` | Codec support depends on OpenCV/FFmpeg |
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
