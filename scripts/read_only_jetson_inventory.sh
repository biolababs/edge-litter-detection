#!/usr/bin/env bash

# Read-only Jetson inventory. This script writes nothing, installs nothing,
# changes no services, and does not invoke sudo.

set -u

section() {
  printf '\n===== %s =====\n' "$1"
}

section "identity"
hostname 2>/dev/null || true
id 2>/dev/null || true
date -Is 2>/dev/null || true

section "device"
tr -d '\000' </proc/device-tree/model 2>/dev/null || true
printf '\n'
cat /proc/device-tree/compatible 2>/dev/null | tr '\000' '\n' || true

section "operating_system"
cat /etc/os-release 2>/dev/null || true
uname -a 2>/dev/null || true
cat /etc/nv_tegra_release 2>/dev/null || true

section "jetpack_and_l4t"
dpkg-query -W -f='${binary:Package}\t${Version}\n' \
  nvidia-jetpack nvidia-l4t-core nvidia-l4t-cuda nvidia-l4t-tensorrt \
  nvidia-l4t-multimedia 2>/dev/null || true

section "power_mode_read_only"
nvpmodel -q 2>&1 || true
jetson_clocks --show 2>&1 || true

section "cpu"
lscpu 2>/dev/null || true

section "memory"
free -h 2>/dev/null || true
grep -E 'MemTotal|MemAvailable|SwapTotal|SwapFree' /proc/meminfo 2>/dev/null || true

section "storage"
df -hT / 2>/dev/null || true
lsblk -o NAME,TYPE,SIZE,FSTYPE,MOUNTPOINTS,MODEL 2>/dev/null || true

section "cuda_tensorrt_tools"
for tool in python3 nvcc trtexec tegrastats docker nvidia-smi; do
  printf '%-12s ' "$tool"
  command -v "$tool" 2>/dev/null || printf 'not-found\n'
done
nvcc --version 2>/dev/null || true
trtexec --version 2>/dev/null || true

section "python"
python3 --version 2>/dev/null || true
python3 - <<'PY' 2>/dev/null || true
import importlib.metadata as metadata
import platform

print("machine=" + platform.machine())
for name in (
    "torch",
    "torchvision",
    "transformers",
    "tensorrt",
    "rfdetr",
    "opencv-python",
    "numpy",
    "onnx",
    "onnxruntime-gpu",
):
    try:
        print(f"{name}={metadata.version(name)}")
    except metadata.PackageNotFoundError:
        pass

try:
    import torch
    print(f"torch_cuda_available={torch.cuda.is_available()}")
    print(f"torch_cuda_version={torch.version.cuda}")
    if torch.cuda.is_available():
        print(f"torch_device={torch.cuda.get_device_name(0)}")
except Exception as error:
    print(f"torch_probe_error={type(error).__name__}")

try:
    import cv2
    print(f"opencv={cv2.__version__}")
    print("opencv_cuda_devices=" + str(cv2.cuda.getCudaEnabledDeviceCount()))
except Exception as error:
    print(f"opencv_probe_error={type(error).__name__}")
PY

section "resource_snapshot"
uptime 2>/dev/null || true
ps -eo user=,pid=,comm=,%cpu=,%mem=,rss= --sort=-%cpu 2>/dev/null | head -n 21 || true

section "containers_read_only"
docker ps --format '{{.Names}}|{{.Image}}|{{.Status}}' 2>/dev/null || true

section "listening_ports_without_process_arguments"
ss -lntup 2>/dev/null | sed -n '1,80p' || true

section "thermal_and_gpu_snapshot"
for zone in /sys/class/thermal/thermal_zone*; do
  [ -r "$zone/type" ] || continue
  zone_type=$(cat "$zone/type" 2>/dev/null || true)
  zone_temp=$(cat "$zone/temp" 2>/dev/null || true)
  printf '%s=%s\n' "$zone_type" "$zone_temp"
done
cat /sys/devices/gpu.0/load 2>/dev/null || true

section "camera_devices"
for device in /dev/video*; do
  [ -e "$device" ] && printf '%s\n' "$device"
done

section "inventory_complete"
printf 'No write, install, restart, container mutation, or configuration command was executed.\n'
