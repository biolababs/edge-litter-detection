#!/usr/bin/env bash
set -Eeuo pipefail

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$project_root"
venv_dir="${LITTER_VENV:-$project_root/.venv}"
python_command="${LITTER_PYTHON:-}"
source_value="${LITTER_SOURCE:-auto}"
backend_value="${LITTER_BACKEND:-grounding_dino}"
model_path="${LITTER_MODEL:-}"
model_was_set=false
if [[ -n "$model_path" ]]; then
  model_was_set=true
fi
model_url="${LITTER_MODEL_URL:-}"
model_sha256="${LITTER_MODEL_SHA256:-}"
device_value="${LITTER_DEVICE:-auto}"
database_path="${LITTER_DATABASE:-$project_root/state/litter-edge.db}"
edge_device_id="${LITTER_EDGE_DEVICE_ID:-edge-node}"
vehicle_id="${LITTER_VEHICLE_ID:-}"
route_id="${LITTER_ROUTE_ID:-}"
separation_config="${LITTER_SEPARATION_CONFIG:-$project_root/config/separation.yaml}"
mode="infer"
display_mode="auto"
skip_install=false
reinstall=false
list_cameras=false
force_model_download=false
database_enabled=true
persist_detections=false
max_frames=0
demo_data=false
demo_limit="${LITTER_DEMO_LIMIT:-8}"

usage() {
  cat <<'EOF'
Usage: ./startup.sh [options]

Default behavior:
  1. Create .venv and install the application.
  2. Download/cache the public Grounding DINO Tiny model on first use.
  3. Select the first working camera, or the first file under media/.
  4. Run detection, classification, tracking, counting, and separation guidance.
  5. Persist operational counts to state/litter-edge.db.

Options:
  --source VALUE         Image, video, camera index, stream URL, or "auto".
  --backend NAME         grounding_dino (default) or rfdetr.
  --model VALUE          Public model ID or local RF-DETR checkpoint path.
  --model-url URL        Optional HTTPS URL for an RF-DETR checkpoint.
  --model-sha256 DIGEST  Required SHA-256 for --model-url.
  --device VALUE         auto, cpu, cuda, cuda:0, etc.
  --database PATH        SQLite count/observation store.
  --no-database          Disable SQLite persistence for this run.
  --persist-detections   Store every detection row, not only counts/events.
  --edge-device-id ID    Stable identifier for this edge computer.
  --vehicle-id ID        Optional truck or collection vehicle identifier.
  --route-id ID          Optional route, shift, or work-order identifier.
  --separation-config P  Material-to-separation-stream policy.
  --display              Force the live display window.
  --no-display           Disable the display window.
  --max-frames N         Stop after N frames; zero means unlimited.
  --demo                  Download attributed public test images and run one.
  --demo-limit N          Number of test images to cache (default: 8).
  --api                   Start the HTTP API instead of media inference.
  --counts-api            Start the database/review API without requiring a model.
  --list-cameras          Install dependencies and list attached cameras.
  --skip-install          Reuse the existing environment without pip install.
  --reinstall             Refresh dependencies even if setup already completed.
  --force-model-download  Replace an existing checkpoint after verification.
  -h, --help              Show this help.

Environment equivalents:
  LITTER_SOURCE, LITTER_BACKEND, LITTER_MODEL, LITTER_MODEL_URL,
  LITTER_MODEL_SHA256, LITTER_DEVICE, LITTER_DATABASE, LITTER_EDGE_DEVICE_ID,
  LITTER_VEHICLE_ID, LITTER_ROUTE_ID, LITTER_SEPARATION_CONFIG, LITTER_VENV,
  LITTER_DEMO_LIMIT, and LITTER_PYTHON.
EOF
}

fail() {
  printf 'ERROR: %s\n' "$*" >&2
  exit 1
}

source_for_log() {
  if [[ "$1" == *"://"* ]]; then
    printf '%s\n' "live stream (URL and credentials hidden)"
  else
    printf '%s\n' "$1"
  fi
}

select_bootstrap_python() {
  local candidate
  local resolved
  for candidate in python3.12 python3.11 python3.10 python3; do
    resolved="$(command -v "$candidate" 2>/dev/null || true)"
    if [[ -n "$resolved" ]] && "$resolved" -c \
      'import sys; raise SystemExit(0 if (3, 10) <= sys.version_info < (3, 13) else 1)'
    then
      printf '%s\n' "$resolved"
      return 0
    fi
  done
  return 1
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --source)
      [[ $# -ge 2 ]] || fail "--source requires a value."
      source_value="$2"
      shift 2
      ;;
    --backend)
      [[ $# -ge 2 ]] || fail "--backend requires a value."
      backend_value="$2"
      shift 2
      ;;
    --model)
      [[ $# -ge 2 ]] || fail "--model requires a value."
      model_path="$2"
      model_was_set=true
      shift 2
      ;;
    --model-url)
      [[ $# -ge 2 ]] || fail "--model-url requires a URL."
      model_url="$2"
      shift 2
      ;;
    --model-sha256)
      [[ $# -ge 2 ]] || fail "--model-sha256 requires a digest."
      model_sha256="$2"
      shift 2
      ;;
    --device)
      [[ $# -ge 2 ]] || fail "--device requires a value."
      device_value="$2"
      shift 2
      ;;
    --database)
      [[ $# -ge 2 ]] || fail "--database requires a path."
      database_path="$2"
      shift 2
      ;;
    --no-database)
      database_enabled=false
      shift
      ;;
    --persist-detections)
      persist_detections=true
      shift
      ;;
    --edge-device-id)
      [[ $# -ge 2 ]] || fail "--edge-device-id requires a value."
      edge_device_id="$2"
      shift 2
      ;;
    --vehicle-id)
      [[ $# -ge 2 ]] || fail "--vehicle-id requires a value."
      vehicle_id="$2"
      shift 2
      ;;
    --route-id)
      [[ $# -ge 2 ]] || fail "--route-id requires a value."
      route_id="$2"
      shift 2
      ;;
    --separation-config)
      [[ $# -ge 2 ]] || fail "--separation-config requires a path."
      separation_config="$2"
      shift 2
      ;;
    --display)
      display_mode="on"
      shift
      ;;
    --no-display)
      display_mode="off"
      shift
      ;;
    --max-frames)
      [[ $# -ge 2 ]] || fail "--max-frames requires a value."
      max_frames="$2"
      shift 2
      ;;
    --demo)
      demo_data=true
      shift
      ;;
    --demo-limit)
      [[ $# -ge 2 ]] || fail "--demo-limit requires a value."
      demo_limit="$2"
      shift 2
      ;;
    --api)
      mode="api"
      shift
      ;;
    --counts-api)
      mode="counts_api"
      shift
      ;;
    --list-cameras)
      list_cameras=true
      shift
      ;;
    --skip-install)
      skip_install=true
      shift
      ;;
    --reinstall)
      reinstall=true
      shift
      ;;
    --force-model-download)
      force_model_download=true
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      fail "Unknown option: $1"
      ;;
  esac
done

[[ "$max_frames" =~ ^[0-9]+$ ]] || fail "--max-frames must be a non-negative integer."
[[ "$demo_limit" =~ ^[1-9][0-9]*$ ]] || fail \
  "--demo-limit must be a positive integer."
(( demo_limit <= 100 )) || fail "--demo-limit must not exceed 100."
case "$(printf '%s' "$backend_value" | tr '[:upper:]-' '[:lower:]_')" in
  grounding_dino)
    backend_value="grounding_dino"
    ;;
  rfdetr)
    backend_value="rfdetr"
    ;;
  *)
    fail "--backend must be grounding_dino or rfdetr."
    ;;
esac
if [[ "$model_was_set" != true ]]; then
  if [[ "$backend_value" == "rfdetr" ]]; then
    model_path="$project_root/models/rfdetr-nano-litter.pth"
  else
    model_path="IDEA-Research/grounding-dino-tiny"
  fi
fi
if [[ "$mode" != "infer" && "$database_enabled" != true ]]; then
  fail "--no-database is supported only for media inference."
fi
if [[ "$mode" != "infer" && "$demo_data" == true ]]; then
  fail "--demo is supported only for media inference."
fi

if [[ -z "$python_command" ]]; then
  if [[ "$skip_install" == true && ! -x "$venv_dir/bin/python" ]]; then
    fail "--skip-install requires an existing environment at $venv_dir."
  fi
  if [[ ! -x "$venv_dir/bin/python" ]]; then
    bootstrap_python="$(select_bootstrap_python)" || fail \
      "Python 3.10 or newer was not found. Install Python 3.10-3.12 and rerun."
    if [[ -f /etc/nv_tegra_release ]]; then
      fail "Jetson detected. Generic PyTorch installation is disabled.

Create an isolated JetPack-compatible environment during an authorized
maintenance window, then run:
  LITTER_PYTHON=/path/to/environment/bin/python ./startup.sh [options]"
    fi
    "$bootstrap_python" -m venv "$venv_dir"
  fi
  python_command="$venv_dir/bin/python"
fi
if [[ "$python_command" != */* ]]; then
  python_command="$(command -v "$python_command" 2>/dev/null || true)"
fi
[[ -x "$python_command" ]] || fail "Python is not executable: $python_command"
"$python_command" -c \
  'import sys; raise SystemExit(0 if (3, 10) <= sys.version_info < (3, 13) else 1)' ||
  fail "The selected Python must be version 3.10, 3.11, or 3.12."

if [[ "$backend_value" == "rfdetr" && "$model_path" != /* ]]; then
  model_path="$project_root/$model_path"
fi
if [[ "$database_path" != /* ]]; then
  database_path="$project_root/$database_path"
fi
if [[ "$separation_config" != /* ]]; then
  separation_config="$project_root/$separation_config"
fi
[[ -n "$edge_device_id" ]] || fail "--edge-device-id cannot be empty."
[[ -f "$separation_config" ]] || fail \
  "Separation configuration not found: $separation_config"
mkdir -p \
  "$project_root/models" \
  "$project_root/runs" \
  "$project_root/reports/generated" \
  "$(dirname "$database_path")"

runtime_extra="runtime"
if [[ "$display_mode" == "off" || \
  ( "$display_mode" == "auto" && "$(uname -s)" != "Darwin" && \
    -z "${DISPLAY:-}" && -z "${WAYLAND_DISPLAY:-}" ) ]]
then
  runtime_extra="runtime-headless"
fi

install_profile="$runtime_extra"
if [[ "$backend_value" == "rfdetr" ]]; then
  model_extra="rfdetr"
else
  model_extra="public-model"
fi
install_extras="$runtime_extra,$model_extra"
if [[ "$list_cameras" == true ]]; then
  install_profile="discovery"
  install_extras="runtime-headless"
elif [[ "$mode" == "api" ]]; then
  install_profile="api-$backend_value"
  install_extras="runtime-headless,$model_extra,api"
elif [[ "$mode" == "counts_api" ]]; then
  install_profile="counts-api"
  install_extras="api"
fi
if [[ "$install_profile" == "runtime" || "$install_profile" == "runtime-headless" ]]; then
  install_profile="$install_profile-$backend_value"
fi
install_marker="$venv_dir/.edge-litter-$install_profile-0.8.0"

if [[ "$skip_install" != true && ( "$reinstall" == true || ! -f "$install_marker" ) ]]; then
  "$python_command" -m pip install --upgrade pip
  "$python_command" -m pip install -e ".[$install_extras]"
  if [[ "$python_command" == "$venv_dir/bin/python" ]]; then
    : >"$install_marker"
  fi
fi

if [[ "$list_cameras" == true ]]; then
  exec "$python_command" "$project_root/discover_sources.py" --list-cameras
fi

if [[ "$demo_data" == true ]]; then
  printf 'Preparing attributed TACO demo images...\n'
  source_value="$(
    "$python_command" "$project_root/prepare_test_data.py" \
      --output "$project_root/media/taco-demo" \
      --limit "$demo_limit" \
      --format path
  )"
  [[ -f "$source_value" ]] || fail \
    "Demo data preparation did not return a readable image."
  printf '  attribution: %s\n' "$project_root/media/taco-demo/manifest.json"
fi

if [[ "$backend_value" != "rfdetr" && \
  ( -n "$model_url" || -n "$model_sha256" || "$force_model_download" == true ) ]]
then
  fail "--model-url, --model-sha256, and --force-model-download apply only to rfdetr."
fi

model_release_file="$project_root/config/model-release.json"
if [[ "$backend_value" == "rfdetr" && "$mode" != "counts_api" && \
  ( ! -f "$model_path" || "$force_model_download" == true ) && \
  -z "$model_url" && -f "$model_release_file" ]]
then
  IFS=$'\t' read -r configured_model_url configured_model_sha256 < <(
    "$python_command" -c '
import json
import sys

with open(sys.argv[1], encoding="utf-8") as handle:
    payload = json.load(handle)

url = payload.get("url") or ""
sha256 = payload.get("sha256") or ""
print(url + "\t" + sha256)
' "$model_release_file"
  )
  if [[ -n "$configured_model_url" ]]; then
    model_url="$configured_model_url"
    model_sha256="$configured_model_sha256"
  fi
fi

if [[ "$backend_value" == "rfdetr" && "$mode" != "counts_api" && \
  ! -f "$model_path" && -z "$model_url" ]]
then
  discovered_model="$(
    find "$project_root/models" -maxdepth 1 -type f -name '*.pth' -print |
      sort | head -n 1
  )"
  if [[ -n "$discovered_model" ]]; then
    model_path="$discovered_model"
  elif [[ -t 0 ]]; then
    read -r -p "Path to trained RF-DETR litter checkpoint: " supplied_model
    if [[ -n "$supplied_model" ]]; then
      if [[ "$supplied_model" != /* ]]; then
        supplied_model="$project_root/$supplied_model"
      fi
      model_path="$supplied_model"
    fi
  fi
fi

if [[ "$backend_value" == "rfdetr" && "$mode" != "counts_api" && \
  ( ! -f "$model_path" || "$force_model_download" == true ) ]]
then
  if [[ -n "$model_url" ]]; then
    [[ -n "$model_sha256" ]] || fail \
      "LITTER_MODEL_SHA256 or --model-sha256 is required for model download."
    download_arguments=(
      "$python_command"
      "$project_root/download_model.py"
      --url "$model_url"
      --sha256 "$model_sha256"
      --output "$model_path"
    )
    if [[ "$force_model_download" == true ]]; then
      download_arguments+=(--force)
    fi
    "${download_arguments[@]}"
  else
    fail "RF-DETR checkpoint not found at $model_path.

Provide one of:
  ./startup.sh --backend rfdetr --model /path/to/model.pth
  ./startup.sh --backend rfdetr --model-url HTTPS_URL --model-sha256 SHA256

For the public no-training model, run ./startup.sh without --backend."
  fi
fi

if [[ "$mode" == "api" || "$mode" == "counts_api" ]]; then
  export LITTER_BACKEND="$backend_value"
  export LITTER_MODEL="$model_path"
  export LITTER_DEVICE="$device_value"
  export LITTER_DATABASE="$database_path"
  export LITTER_EDGE_DEVICE_ID="$edge_device_id"
  export LITTER_VEHICLE_ID="$vehicle_id"
  export LITTER_ROUTE_ID="$route_id"
  export LITTER_SEPARATION_CONFIG="$separation_config"
  if [[ "$mode" == "counts_api" ]]; then
    export LITTER_COUNTS_ONLY=true
  fi
  exec "$python_command" "$project_root/serve.py"
fi

if [[ "$source_value" == "auto" ]]; then
  camera_report="$(
    "$python_command" "$project_root/discover_sources.py" --list-cameras 2>/dev/null || true
  )"
  source_value="$(
    printf '%s' "$camera_report" |
      "$python_command" -c '
import json
import sys

try:
    payload = json.load(sys.stdin)
except (json.JSONDecodeError, TypeError):
    payload = {}

for camera in payload.get("cameras", []):
    if camera.get("frame_read"):
        print(camera["source"])
        break
'
  )"

  if [[ -z "$source_value" && -d "$project_root/media" ]]; then
    source_value="$(
      find "$project_root/media" -maxdepth 1 -type f \
        \( -iname '*.jpg' -o -iname '*.jpeg' -o -iname '*.png' \
        -o -iname '*.webp' -o -iname '*.mp4' -o -iname '*.mov' \
        -o -iname '*.mkv' -o -iname '*.avi' \) \
        -print | sort | head -n 1
    )"
  fi

  if [[ -z "$source_value" && -t 0 ]]; then
    read -r -p "Image/video path, camera index, or stream URL: " source_value
  fi
  [[ -n "$source_value" ]] || fail \
    "No working camera or media file was found. Pass --source VALUE."
fi

if ! "$python_command" "$project_root/discover_sources.py" \
  --source "$source_value" >/dev/null
then
  fail "Unable to read source: $(source_for_log "$source_value")"
fi

run_timestamp="$(date -u '+%Y%m%dT%H%M%SZ')"
output_root="$project_root/reports/generated"
mkdir -p "$output_root"
events_output="$output_root/run-$run_timestamp.jsonl"
summary_output="$output_root/run-$run_timestamp-summary.json"

inference_arguments=(
  "$python_command"
  "$project_root/infer.py"
  --source "$source_value"
  --backend "$backend_value"
  --model "$model_path"
  --device "$device_value"
  --separation-config "$separation_config"
  --events-output "$events_output"
  --output "$summary_output"
  --max-frames "$max_frames"
)
if [[ "$database_enabled" == true ]]; then
  inference_arguments+=(
    --database "$database_path"
    --edge-device-id "$edge_device_id"
  )
  if [[ -n "$vehicle_id" ]]; then
    inference_arguments+=(--vehicle-id "$vehicle_id")
  fi
  if [[ -n "$route_id" ]]; then
    inference_arguments+=(--route-id "$route_id")
  fi
  if [[ "$persist_detections" == true ]]; then
    inference_arguments+=(--persist-detections)
  fi
else
  inference_arguments+=(--no-database --edge-device-id "$edge_device_id")
fi

source_lower="$(printf '%s' "$source_value" | tr '[:upper:]' '[:lower:]')"
source_is_camera=false
if [[ "$source_value" =~ ^[0-9]+$ ]]; then
  source_is_camera=true
fi
if [[ "$source_lower" =~ \.(jpg|jpeg|png|bmp|tif|tiff|webp)$ ]]; then
  inference_arguments+=(
    --annotated-output "$output_root/run-$run_timestamp-annotated.jpg"
  )
elif [[ "$source_is_camera" != true && "$source_value" != *"://"* ]]; then
  inference_arguments+=(
    --annotated-output "$output_root/run-$run_timestamp-annotated.mp4"
  )
fi

if [[ "$display_mode" == "on" ]]; then
  inference_arguments+=(--display)
elif [[ "$display_mode" == "auto" ]]; then
  if [[ "$source_is_camera" == true || "$source_value" == *"://"* ]]; then
    if [[ "$(uname -s)" == "Darwin" || -n "${DISPLAY:-}" || -n "${WAYLAND_DISPLAY:-}" ]]; then
      inference_arguments+=(--display)
    fi
  fi
fi

printf 'Starting litter detection\n'
printf '  source: %s\n' "$(source_for_log "$source_value")"
printf '  backend: %s\n' "$backend_value"
printf '  model:  %s\n' "$model_path"
printf '  events: %s\n' "$events_output"
printf '  summary: %s\n' "$summary_output"
if [[ "$database_enabled" == true ]]; then
  printf '  database: %s\n' "$database_path"
fi
printf '  edge device: %s\n' "$edge_device_id"
if [[ -n "$vehicle_id" ]]; then
  printf '  vehicle: %s\n' "$vehicle_id"
fi
if [[ -n "$route_id" ]]; then
  printf '  route: %s\n' "$route_id"
fi

exec "${inference_arguments[@]}"
