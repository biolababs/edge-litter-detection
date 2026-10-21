#!/usr/bin/env bash
set -Eeuo pipefail

repository_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
test_directory="$(mktemp -d /tmp/edge-litter-startup.XXXXXX)"
trap 'rm -rf "$test_directory"' EXIT

fake_python="$test_directory/python"
fake_model="$test_directory/model.pth"
fake_log="$test_directory/python.log"
fake_demo_image="$test_directory/demo.jpg"
fake_venv="$test_directory/venv"

cat >"$fake_python" <<'EOF'
#!/usr/bin/env bash
set -Eeuo pipefail

printf '%s\n' "$*" >>"$FAKE_PYTHON_LOG"

case "${1:-}" in
  -c)
    ;;
  -m)
    ;;
  *discover_sources.py)
    if [[ " $* " == *" --list-cameras "* ]]; then
      printf '%s\n' '{"cameras":[{"source":"0","frame_read":true}]}'
    fi
    ;;
  *prepare_test_data.py)
    printf '%s\n' "$FAKE_DEMO_IMAGE"
    ;;
  *infer.py)
    ;;
  *serve.py)
    printf 'counts-only=%s\n' "${LITTER_COUNTS_ONLY:-false}" >>"$FAKE_PYTHON_LOG"
    ;;
  *)
    printf 'Unexpected fake-Python invocation: %s\n' "$*" >&2
    exit 1
    ;;
esac
EOF

chmod +x "$fake_python"
: >"$fake_model"
: >"$fake_demo_image"

FAKE_PYTHON_LOG="$fake_log" \
LITTER_PYTHON="$fake_python" \
  "$repository_root/startup.sh" \
  --skip-install \
  --source 0 \
  --no-display \
  --max-frames 1 >/dev/null

grep -F "$repository_root/infer.py" "$fake_log" >/dev/null
grep -F -- "--backend grounding_dino" "$fake_log" >/dev/null
grep -F -- "--model IDEA-Research/grounding-dino-tiny" "$fake_log" >/dev/null
grep -F -- "--source 0" "$fake_log" >/dev/null
grep -F -- "--max-frames 1" "$fake_log" >/dev/null

: >"$fake_log"
FAKE_DEMO_IMAGE="$fake_demo_image" \
FAKE_PYTHON_LOG="$fake_log" \
LITTER_PYTHON="$fake_python" \
  "$repository_root/startup.sh" \
  --skip-install \
  --demo \
  --demo-limit 3 \
  --no-display >/dev/null

grep -F "$repository_root/prepare_test_data.py" "$fake_log" >/dev/null
grep -F -- "--limit 3" "$fake_log" >/dev/null
grep -F -- "--format path" "$fake_log" >/dev/null
grep -F "$repository_root/infer.py" "$fake_log" >/dev/null
grep -F -- "--source $fake_demo_image" "$fake_log" >/dev/null

if FAKE_DEMO_IMAGE="$fake_demo_image" \
  FAKE_PYTHON_LOG="$fake_log" \
  LITTER_PYTHON="$fake_python" \
    "$repository_root/startup.sh" \
    --skip-install \
    --demo \
    --counts-api >/dev/null 2>&1
then
  printf '%s\n' "--demo unexpectedly accepted --counts-api." >&2
  exit 1
fi

mkdir -p "$fake_venv/bin"
cp "$fake_python" "$fake_venv/bin/python"
: >"$fake_log"
FAKE_PYTHON_LOG="$fake_log" \
LITTER_VENV="$fake_venv" \
  "$repository_root/startup.sh" \
  --source 0 \
  --no-display \
  --max-frames 1 >/dev/null

grep -F -- "-e .[runtime-headless,public-model]" "$fake_log" >/dev/null

FAKE_PYTHON_LOG="$fake_log" \
LITTER_PYTHON="$fake_python" \
  "$repository_root/startup.sh" \
  --skip-install \
  --backend rfdetr \
  --model "$fake_model" \
  --source 0 \
  --no-display \
  --max-frames 1 >/dev/null

grep -F -- "--backend rfdetr" "$fake_log" >/dev/null
grep -F -- "--model $fake_model" "$fake_log" >/dev/null

: >"$fake_log"
FAKE_PYTHON_LOG="$fake_log" \
LITTER_PYTHON="$fake_python" \
  "$repository_root/startup.sh" \
  --skip-install \
  --backend omdet_turbo \
  --source 0 \
  --no-display \
  --max-frames 1 >/dev/null

grep -F -- "--backend omdet_turbo" "$fake_log" >/dev/null
grep -F -- "--model omlab/omdet-turbo-swin-tiny-hf" "$fake_log" >/dev/null

stream_output="$(
  FAKE_PYTHON_LOG="$fake_log" \
  LITTER_PYTHON="$fake_python" \
    "$repository_root/startup.sh" \
    --skip-install \
    --source "rtsp://user:secret@example.test/live?token=abc" \
    --no-display \
    --max-frames 1
)"

grep -F "live stream (URL and credentials hidden)" <<<"$stream_output" >/dev/null
if grep -F "user:secret" <<<"$stream_output" >/dev/null; then
  printf 'Launcher output exposed stream credentials.\n' >&2
  exit 1
fi

FAKE_PYTHON_LOG="$fake_log" \
LITTER_PYTHON="$fake_python" \
  "$repository_root/startup.sh" \
  --skip-install \
  --counts-api \
  --database "$test_directory/counts.db" >/dev/null

grep -F "$repository_root/serve.py" "$fake_log" >/dev/null
grep -F "counts-only=true" "$fake_log" >/dev/null
