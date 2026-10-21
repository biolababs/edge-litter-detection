# Local media

Place downloaded test images or videos in this directory. The files themselves
are ignored by Git so private or licensed media is not published accidentally.

Examples:

```bash
./startup.sh --source ./media/litter.jpg
./startup.sh --source ./media/litter.mp4
```

With `--source auto`, `startup.sh` selects the first supported file here when
no working local camera is found.

For a reproducible public functional sample:

```bash
./startup.sh --demo
```

Or download the sample without running inference:

```bash
python prepare_test_data.py --limit 8
```

The downloader writes images and `media/taco-demo/manifest.json` locally. The
manifest retains upstream URLs, checksums, categories, and per-image license
metadata. Both the media and manifest are ignored by Git.

For a reproducible recycling-line video pipeline test:

```bash
./startup.sh --backend omdet_turbo --demo-video --no-display
```

Or download the video without starting inference:

```bash
python prepare_demo_video.py
```

The video and its source, creator, license, and checksum manifest are written
under `media/demo-video/` and remain ignored by Git. This media exercises
capture and stream processing on a material-recovery-facility conveyor; it is
not a labelled accuracy dataset. The downloaded video remains under its
upstream CC BY-SA 3.0 license and is not relicensed under Apache-2.0.
