#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="${SCRIPT_DIR%/scripts}"
ENV_NAME="nova"

echo "[Nova Setup] Initializing WSL environment..."

if ! command -v conda >/dev/null 2>&1; then
  echo "[Nova Setup] Conda is required but not found. Install Miniconda inside WSL2 and retry." >&2
  exit 1
fi

# Load conda into the current shell session
__conda_setup="$(conda shell.bash hook 2>/dev/null)" || {
  echo "[Nova Setup] Unable to load Conda shell integration." >&2
  exit 1
}
eval "$__conda_setup"
unset __conda_setup

if conda info --envs | awk '{print $1}' | grep -qx "$ENV_NAME"; then
  echo "[Nova Setup] Environment '$ENV_NAME' already exists. Skipping creation."
else
  echo "[Nova Setup] Creating Conda environment '$ENV_NAME' (Python 3.11)..."
  conda create -n "$ENV_NAME" python=3.11 -y
fi

conda activate "$ENV_NAME"

cd "$REPO_ROOT"

echo "[Nova Setup] Upgrading pip..."
pip install --upgrade pip

echo "[Nova Setup] Installing CUDA-enabled PyTorch (cu121 wheels)..."
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121

echo "[Nova Setup] Installing core project requirements..."
pip install -r requirements.txt

echo "[Nova Setup] Installing NVIDIA NeMo TTS stack..."
pip install --extra-index-url https://pypi.nvidia.com nemo_toolkit[tts]

echo "[Nova Setup] Installing pynini (Linux wheels)..."
pip install pynini

python - <<'PY'
import torch

if not torch.cuda.is_available():
    raise SystemExit("[Nova Setup] torch.cuda.is_available() returned False. Ensure your GPU drivers and CUDA toolkit are visible inside WSL2.")

print("[Nova Setup] CUDA detected. Device count:", torch.cuda.device_count())
PY

echo "✅ WSL environment ready. Run 'python scripts/tts_smoketest.py' to test voice synthesis."
