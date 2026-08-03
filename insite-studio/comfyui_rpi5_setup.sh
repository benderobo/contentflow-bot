#!/bin/bash
# ============================================================
# IN_SITE Premium — ComfyUI + SD 1.5 for Raspberry Pi 5
# Target: BenderPi (100.112.44.14), 8GB RAM, 4 cores, Debian 13
# ============================================================
set -e

INSTALL_DIR="$HOME/comfyui-in-site"
VENV_DIR="$INSTALL_DIR/venv"
MODELS_DIR="$INSTALL_DIR/models"
OUTPUT_DIR="$HOME/in-site-output"
PORT=8188

echo "=========================================="
echo " IN_SITE Premium — ComfyUI + SD 1.5 Setup"
echo " Raspberry Pi 5 (aarch64, CPU-only)"
echo "=========================================="

# --- 1. System dependencies ---
echo "[1/8] Installing system dependencies..."
sudo apt-get update -qq
sudo apt-get install -y -qq \
  python3-venv python3-dev \
  libopenblas-dev libopenblas-base \
  libjpeg-dev libpng-dev libfreetype6-dev \
  git wget curl build-essential \
  libhdf5-dev liblapack-dev \
  > /dev/null 2>&1
echo "  ✓ System deps installed"

# --- 2. Create directories ---
echo "[2/8] Creating directories..."
mkdir -p "$INSTALL_DIR" "$MODELS_DIR/checkpoints" "$MODELS_DIR/vae" "$MODELS_DIR/lora" "$OUTPUT_DIR"
echo "  ✓ Directories created"

# --- 3. Python venv + PyTorch CPU ---
echo "[3/8] Setting up Python venv with PyTorch CPU..."
python3 -m venv "$VENV_DIR"
source "$VENV_DIR/bin/activate"

pip install --upgrade pip > /dev/null 2>&1
pip install torch torchvision torchaudio \
  --index-url https://download.pytorch.org/whl/cpu \
  > /dev/null 2>&1
echo "  ✓ PyTorch CPU installed ($(python3 -c 'import torch; print(torch.__version__)'))"

# --- 4. ComfyUI ---
echo "[4/8] Cloning ComfyUI..."
if [ -d "$INSTALL_DIR/ComfyUI" ]; then
  echo "  ⚠ ComfyUI already exists, pulling latest..."
  cd "$INSTALL_DIR/ComfyUI" && git pull > /dev/null 2>&1
else
  git clone https://github.com/comfyanonymous/ComfyUI.git "$INSTALL_DIR/ComfyUI"
fi
cd "$INSTALL_DIR/ComfyUI"
pip install -r requirements.txt > /dev/null 2>&1
echo "  ✓ ComfyUI installed"

# --- 5. SD 1.5 model (runwayml/stable-diffusion-v1-5) ---
echo "[5/8] Downloading Stable Diffusion 1.5 model (~4GB)..."
SD_MODEL="$MODELS_DIR/checkpoints/v1-5-pruned-emaonly.safetensors"
if [ -f "$SD_MODEL" ]; then
  echo "  ⚠ Model already exists, skipping"
else
  wget -q --show-progress -O "$SD_MODEL" \
    "https://huggingface.co/stable-diffusion-v1-5/stable-diffusion-v1-5/resolve/main/v1-5-pruned-emaonly.safetensors"
  echo "  ✓ SD 1.5 model downloaded"
fi

# --- 6. SD 1.5 VAE ---
echo "[6/8] Downloading SD 1.5 VAE..."
VAE_MODEL="$MODELS_DIR/vae/vae-ft-mse-840000-ema-pruned.safetensors"
if [ -f "$VAE_MODEL" ]; then
  echo "  ⚠ VAE already exists, skipping"
else
  wget -q --show-progress -O "$VAE_MODEL" \
    "https://huggingface.co/stabilityai/sd-vae-ft-mse-original/resolve/main/vae-ft-mse-840000-ema-pruned.safetensors"
  echo "  ✓ VAE downloaded"
fi

# --- 7. ComfyUI systemd service ---
echo "[7/8] Creating systemd service..."
sudo tee /etc/systemd/system/comfyui-in-site.service > /dev/null << EOF
[Unit]
Description=ComfyUI IN_SITE Premium
After=network.target

[Service]
Type=simple
User=$(whoami)
WorkingDirectory=$INSTALL_DIR/ComfyUI
ExecStart=$VENV_DIR/bin/python main.py --listen 0.0.0.0 --port $PORT --cpu --preview-method auto
Restart=always
RestartSec=5
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable comfyui-in-site.service
echo "  ✓ Service created and enabled"

# --- 8. IN_SITE integration config ---
echo "[8/8] Writing IN_SITE integration config..."
cat > "$INSTALL_DIR/in_site_config.json" << 'CFG'
{
  "service": "comfyui-in-site",
  "host": "0.0.0.0",
  "port": 8188,
  "models": {
    "checkpoint": "v1-5-pruned-emaonly.safetensors",
    "vae": "vae-ft-mse-840000-ema-pruned.safetensors"
  },
  "defaults": {
    "width": 512,
    "height": 512,
    "steps": 20,
    "cfg_scale": 7.5,
    "sampler": "euler_ancestral",
    "scheduler": "normal"
  },
  "output_dir": "$HOME/in-site-output",
  "in_site_integration": {
    "api_endpoint": "http://127.0.0.1:8188/prompt",
    "system_prompt": "IN_SITE Premium image generator — creates website hero images, backgrounds, and visual assets matching the client's brand aesthetic. Style: premium, cinematic, editorial. Color palette derived from client references.",
    "use_cases": [
      "Hero section backgrounds",
      "Service/product illustrations",
      "Social media assets",
      "Brand mood boards",
      "Template preview images"
    ]
  }
}
CFG
echo "  ✓ Config written"

echo ""
echo "=========================================="
echo " ✅ Installation complete!"
echo "=========================================="
echo ""
echo " Start:  sudo systemctl start comfyui-in-site"
echo " Status: sudo systemctl status comfyui-in-site"
echo " Logs:   journalctl -u comfyui-in-site -f"
echo " UI:     http://100.112.44.14:8188"
echo ""
echo " Models: $MODELS_DIR/checkpoints/"
echo " Output: $OUTPUT_DIR/"
echo " Config: $INSTALL_DIR/in_site_config.json"
echo ""
