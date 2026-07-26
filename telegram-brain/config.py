import os
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env'))

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
MEM0_API_KEY = os.getenv("MEM0_API_KEY", "")
MEM0_USER_ID = os.getenv("MEM0_USER_ID", "")
OPENROUTER_KEY = os.getenv("OPENROUTER_API_KEY", "")
GEMINI_API_KEY = os.getenv("GOOGLE_AI_API_KEY", "")

MIMO_CMD = os.getenv("MIMO_CMD", "/root/.mimocode/bin/mimo")
CLAUDE_CMD = os.getenv("CLAUDE_CMD", "/usr/bin/claude")
GH_CMD = os.getenv("GH_CMD", "/usr/bin/gh")

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://100.112.44.14:11434")

SERVERS = {
    "vps": {
        "name": "VPS",
        "host": "167.17.180.42",
        "workdir": "/root",
        "desc": "167.17.180.42\nIN_SITE Studio, n8n, nginx, Docker",
        "type": "local",
    },
    "rpi5": {
        "name": "RPi5",
        "host": "100.112.44.14",
        "workdir": "/root",
        "desc": "benderpi@100.112.44.14\nIN_SITE PREMIUM, Ollama, ComfyUI",
        "ssh": "sshpass -p '0099' ssh -o StrictHostKeyChecking=accept-new -o ConnectTimeout=10 benderpi@100.112.44.14",
        "type": "remote",
    },
    "g0dmod": {
        "name": "G0DMOD",
        "host": "192.168.88.250",
        "workdir": "/home/admin",
        "desc": "Parrot Security (192.168.88.250:2222)\nAI неэтичная модель\nOpenRouter API",
        "ssh": "ssh -o StrictHostKeyChecking=no -p 2222 admin@192.168.88.250",
        "type": "openrouter",
        "model": "openrouter/free",
    },
    "regvps": {
        "name": "666",
        "host": "194.58.66.6",
        "workdir": "/root",
        "desc": "194.58.66.6\nReg.ru VPS, 3x-ui, Ubuntu 24.04",
        "ssh": "ssh -i /root/.ssh/fl_key -o StrictHostKeyChecking=no root@194.58.66.6",
        "type": "remote",
    },
}

DEFAULT_SERVER = "vps"

ALLOWED_USERS = {5264530602}
