#!/usr/bin/env bash
set -Eeuo pipefail

repository_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
test_directory="$(mktemp -d /tmp/edge-litter-startup.XXXXXX)"
trap 'rm -rf "$test_directory"' EXIT

fake_python="$test_directory/python"
fake_model="$test_directory/model.pth"
fake_log="$test_directory/python.log"

cat >"$fake_python" <<'EOF'
#!/usr/bin/env bash
set -Eeuo pipefail

printf '%s\n' "$*" >>"$FAKE_PYTHON_LOG"

case "${1:-}" in
  -c)
    ;;
  *discover_sources.py)
    if [[ " $* " == *" --list-cameras "* ]]; then
      printf '%s\n' '{"cameras":[{"source":"0","frame_read":true}]}'
    fi
    ;;
  *infer.py)
    ;;
  *)
    printf 'Unexpected fake-Python invocation: %s\n' "$*" >&2
    exit 1
    ;;
esac
EOF

chmod +x "$fake_python"
: >"$fake_model"

FAKE_PYTHON_LOG="$fake_log" \
LITTER_PYTHON="$fake_python" \
  "$repository_root/startup.sh" \
  --skip-install \
  --model "$fake_model" \
  --source 0 \
  --no-display \
  --max-frames 1 >/dev/null

grep -F "$repository_root/infer.py" "$fake_log" >/dev/null
grep -F -- "--model $fake_model" "$fake_log" >/dev/null
grep -F -- "--source 0" "$fake_log" >/dev/null
grep -F -- "--max-frames 1" "$fake_log" >/dev/null

stream_output="$(
  FAKE_PYTHON_LOG="$fake_log" \
  LITTER_PYTHON="$fake_python" \
    "$repository_root/startup.sh" \
    --skip-install \
    --model "$fake_model" \
    --source "rtsp://user:secret@example.test/live?token=abc" \
    --no-display \
    --max-frames 1
)"

grep -F "live stream (URL and credentials hidden)" <<<"$stream_output" >/dev/null
if grep -F "user:secret" <<<"$stream_output" >/dev/null; then
  printf 'Launcher output exposed stream credentials.\n' >&2
  exit 1
fi
