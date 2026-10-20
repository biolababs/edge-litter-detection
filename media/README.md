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
