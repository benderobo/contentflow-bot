# IN_SITE Premium — ComfyUI Integration Prompt

## System Prompt (для AI-ассистента IN_SITE)

```
You are IN_SITE Premium Content Generator — a specialized AI assistant for creating visual assets for premium websites.

CAPABILITIES:
- Generate hero section backgrounds and hero images
- Create service/product illustrations
- Produce social media preview assets
- Design brand mood boards and style references
- Generate template preview images for client presentations

STYLE GUIDELINES (from insiteagent.md):
- Premium, cinematic, editorial aesthetic
- Apple/Stripe/Linear level quality
- Clean composition with intentional negative space
- Color psychology: trust, luxury, emotion
- Mobile-first visual hierarchy
- Controlled minimalism with premium motion feel

COLOR SYSTEM (IN_SITE brand):
- Primary Dark: #1C1917 (warm black)
- Primary Gold: #CA8A04 / #C9A84C (luxury, conversion)
- Accent Purple: #7c6af7 (exploration, navigation)
- Light: #FAFAF9 (clean backgrounds)
- Typography: Great Vibes (display), Cormorant Infant (body)

CLIENT CONTEXT (from order):
- Project type: {project_type}
- Niche: {niche}
- Color preferences: {palette}
- Style notes: {style_notes}
- Reference images: attached as base64

OUTPUT RULES:
1. Always generate at 512x512 or 768x768 (RPi5 optimized)
2. Use the client's reference images as style guide
3. Match color palette to client's brand
4. Output: PNG with transparent background option
5. File naming: {order_id}_{asset_type}_{timestamp}.png
```

## API Integration (api_server.py → ComfyUI)

```python
import json
from urllib.request import urlopen, Request

COMFYUI_URL = "http://100.112.44.14:8188/prompt"

def generate_image_comfyui(prompt, negative_prompt="", width=512, height=512, steps=20, seed=-1):
    """Generate image via ComfyUI on RPi5."""
    workflow = {
        "prompt": {
            "3": {
                "class_type": "KSampler",
                "inputs": {
                    "seed": seed if seed >= 0 else int(__import__('random').random() * 2**32),
                    "steps": steps,
                    "cfg": 7.5,
                    "sampler_name": "euler_ancestral",
                    "scheduler": "normal",
                    "denoise": 1.0,
                    "model": ["4", 0],
                    "positive": ["6", 0],
                    "negative": ["7", 0],
                    "latent_image": ["5", 0]
                }
            },
            "4": {
                "class_type": "CheckpointLoaderSimple",
                "inputs": {"ckpt_name": "v1-5-pruned-emaonly.safetensors"}
            },
            "5": {
                "class_type": "EmptyLatentImage",
                "inputs": {"width": width, "height": height, "batch_size": 1}
            },
            "6": {
                "class_type": "CLIPTextEncode",
                "inputs": {"text": prompt, "clip": ["4", 1]}
            },
            "7": {
                "class_type": "CLIPTextEncode",
                "inputs": {"text": negative_prompt or "blurry, low quality, distorted, ugly, watermark, text, logo", "clip": ["4", 1]}
            },
            "8": {
                "class_type": "VAEDecode",
                "inputs": {"samples": ["3", 0], "vae": ["4", 2]}
            },
            "9": {
                "class_type": "SaveImage",
                "inputs": {"filename_prefix": "in_site", "images": ["8", 0]}
            }
        }
    }

    payload = json.dumps(workflow).encode()
    req = Request(COMFYUI_URL, data=payload, headers={"Content-Type": "application/json"})
    resp = urlopen(req, timeout=300)
    return json.loads(resp.read())
```

## Nginx Proxy (optional, for public access)

```nginx
location /comfyui/ {
    proxy_pass http://100.112.44.14:8188/;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;

    # WebSocket support (ComfyUI live preview)
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_read_timeout 300s;
}
```

## PM2 Process (alternative to systemd)

```bash
# On BenderPi:
cd ~/comfyui-in-site/ComfyUI
pm2 start "venv/bin/python main.py --listen 0.0.0.0 --port 8188 --cpu --preview-method auto" \
  --name "comfyui-in-site" \
  --max-memory-restart 6G \
  --log-date-format "YYYY-MM-DD HH:mm:ss"
pm2 save
```

## Quick Commands

```bash
# SSH to RPi5
sshpass -p '0099' ssh benderpi@100.112.44.14

# Start ComfyUI
sudo systemctl start comfyui-in-site

# Check status
sudo systemctl status comfyui-in-site

# View logs
journalctl -u comfyui-in-site -f

# Test API
curl -s http://100.112.44.14:8188/system_stats | python3 -m json.tool

# Generate test image
curl -s -X POST http://100.112.44.14:8188/prompt \
  -H "Content-Type: application/json" \
  -d '{"prompt":{"3":{"class_type":"KSampler","inputs":{"seed":42,"steps":20,"cfg":7.5,"sampler_name":"euler_ancestral","scheduler":"normal","denoise":1,"model":["4",0],"positive":["6",0],"negative":["7",0],"latent_image":["5",0]}},"4":{"class_type":"CheckpointLoaderSimple","inputs":{"ckpt_name":"v1-5-pruned-emaonly.safetensors"}},"5":{"class_type":"EmptyLatentImage","inputs":{"width":512,"height":512,"batch_size":1}},"6":{"class_type":"CLIPTextEncode","inputs":{"text":"premium wedding website hero, golden hour, luxury aesthetic","clip":["4",1]}},"7":{"class_type":"CLIPTextEncode","inputs":{"text":"blurry, low quality, distorted","clip":["4",1]}},"8":{"class_type":"VAEDecode","inputs":{"samples":["3",0],"vae":["4",2]}},"9":{"class_type":"SaveImage","inputs":{"filename_prefix":"test","images":["8",0]}}}}'
```
