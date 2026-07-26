import subprocess
import os
import json
import urllib.request
import urllib.error
import datetime
from config import MIMO_CMD, GH_CMD, SERVERS, OPENROUTER_KEY, OLLAMA_HOST

TIMEOUT = 120


def _openrouter_chat(prompt, model="openrouter/free", system_prompt=None, timeout=60):
    url = "https://openrouter.ai/api/v1/chat/completions"
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})
    payload = {
        "model": model,
        "messages": messages,
        "max_tokens": 4096,
    }
    data = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Authorization", f"Bearer {OPENROUTER_KEY}")
    req.add_header("Content-Type", "application/json")
    req.add_header("HTTP-Referer", "https://mimo-brain.local")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            result = json.loads(resp.read())
            choices = result.get("choices", [])
            if choices:
                msg = choices[0].get("message", {})
                return msg.get("content", "") or msg.get("reasoning", "No content")
            return f"No choices."
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        return f"OpenRouter error {e.code}: {body[:300]}"
    except Exception as e:
        return f"OpenRouter error: {e}"


def ollama_chat(prompt, model="llama3.2:3b", timeout=60):
    url = f"{OLLAMA_HOST}/api/chat"
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
    }
    data = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            result = json.loads(resp.read())
            return result.get("message", {}).get("content", "No content")
    except Exception as e:
        return f"Ollama error: {e}"


def ollama_models():
    url = f"{OLLAMA_HOST}/api/tags"
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            data = json.loads(resp.read())
            models = data.get("models", [])
            return [m.get("name", "?") for m in models]
    except Exception:
        return []


def comfyui_img2img(image_path, prompt, timeout=300):
    import uuid, time
    RPI5_HOST = os.environ.get('RPI5_HOST', '100.112.44.14')
    RPI5_USER = os.environ.get('RPI5_USER', 'benderpi')
    RPI5_PASS = os.environ.get('RPI5_PASS', '0099')
    REMOTE_DIR = f"/home/{RPI5_USER}/comfyui-in-site/uploads"
    REMOTE_SCRIPT = f"/home/{RPI5_USER}/comfyui-in-site/generate_img2img.py"

    unique_id = uuid.uuid4().hex[:8]
    remote_filename = f"tg_{unique_id}.png"
    remote_path = f"{REMOTE_DIR}/{remote_filename}"

    try:
        subprocess.run(
            ["sshpass", "-p", RPI5_PASS, "ssh", "-o", "StrictHostKeyChecking=accept-new",
             f"{RPI5_USER}@{RPI5_HOST}", f"mkdir -p {REMOTE_DIR}"],
            capture_output=True, timeout=10
        )

        subprocess.run(
            ["sshpass", "-p", RPI5_PASS, "scp", "-o", "StrictHostKeyChecking=accept-new",
             image_path, f"{RPI5_USER}@{RPI5_HOST}:{remote_path}"],
            capture_output=True, timeout=30
        )

        cmd = f"cd /home/{RPI5_USER}/comfyui-in-site && python3 {REMOTE_SCRIPT} {remote_path} '{prompt}'"
        result = subprocess.run(
            ["sshpass", "-p", RPI5_PASS, "ssh", "-o", "StrictHostKeyChecking=accept-new",
             f"{RPI5_USER}@{RPI5_HOST}", cmd],
            capture_output=True, text=True, timeout=timeout
        )

        output = result.stdout + result.stderr
        for line in output.split("\n"):
            if "DONE! Image:" in line:
                filename = line.split("Image:")[-1].strip()
                url_line = [l for l in output.split("\n") if "URL:" in l]
                if url_line:
                    url = url_line[-1].split("URL:")[-1].strip()
                    return {"success": True, "filename": filename, "url": url}
            if "Error" in line or "error" in line.lower():
                return {"success": False, "error": line}

        return {"success": False, "error": f"No image produced. Output: {output[-500:]}"}
    except subprocess.TimeoutExpired:
        return {"success": False, "error": "Timed out waiting for ComfyUI"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def gh_command(args, timeout=30):
    try:
        result = subprocess.run(
            [GH_CMD] + args.split(),
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        out = result.stdout.strip()
        err = result.stderr.strip()
        if err and "Warning" not in err:
            out = f"{out}\n{err}" if out else err
        return out[:3000] if out else "(no output)"
    except subprocess.TimeoutExpired:
        return "GitHub CLI timed out."
    except Exception as e:
        return f"GitHub error: {e}"


def run_agent(prompt, server_key="vps", timeout=TIMEOUT):
    server = SERVERS.get(server_key, SERVERS["vps"])
    server_type = server.get("type", "local")
    workdir = server.get("workdir", "/root")
    ssh_cmd = server.get("ssh")

    env = os.environ.copy()
    env["TERM"] = "dumb"
    env["NO_COLOR"] = "1"

    full_prompt = f"{prompt}\n\nRespond concisely. Max 3000 chars."

    if server_type == "openrouter":
        model = server.get("model", "openrouter/free")
        return _openrouter_chat(full_prompt, model=model, timeout=timeout)

    if ssh_cmd:
        cmd_parts = ssh_cmd.split()
        cmd_parts.extend(["bash", "-c", f"'{MIMO_CMD} run \"{full_prompt}\"'"])
        try:
            result = subprocess.run(
                cmd_parts,
                capture_output=True,
                text=True,
                timeout=timeout,
                env=env,
            )
            output = result.stdout.strip()
            if not output and result.stderr:
                output = f"(stderr): {result.stderr[:500]}"
            return output[:4000] if output else "(no output from remote)"
        except subprocess.TimeoutExpired:
            return "Remote timed out (>120s)."
        except Exception as e:
            return f"SSH error: {e}"
    else:
        try:
            result = subprocess.run(
                [MIMO_CMD, "run", full_prompt],
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=workdir,
                env=env,
            )
            output = result.stdout.strip()
            if not output and result.stderr:
                output = f"(stderr): {result.stderr[:500]}"
            return output[:4000] if output else "(no output)"
        except subprocess.TimeoutExpired:
            return "Agent timed out (>120s)."
        except FileNotFoundError:
            return f"MiMoCode not found at {MIMO_CMD}"
        except Exception as e:
            return f"Agent error: {e}"


def run_shell(command, server_key="vps", timeout=30):
    server = SERVERS.get(server_key, SERVERS["vps"])
    ssh_cmd = server.get("ssh")
    server_type = server.get("type", "local")

    if server_type == "openrouter":
        return "Shell not available for API servers."

    try:
        log_entry = datetime.datetime.now().isoformat() + " | server=" + server_key + " | cmd=" + command[:200]
        with open('/tmp/shell_audit.log', 'a') as f:
            f.write(log_entry + "\n")
    except Exception:
        pass

    if ssh_cmd:
        cmd_parts = ssh_cmd.split()
        cmd_parts.extend(["bash", "-c", command])
    else:
        cmd_parts = ["bash", "-c", command]

    try:
        result = subprocess.run(
            cmd_parts,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        out = result.stdout.strip()
        err = result.stderr.strip()
        if err:
            out = f"{out}\n(stderr): {err}" if out else err
        return out[:3000] if out else "(no output)"
    except subprocess.TimeoutExpired:
        return "Command timed out."
    except Exception as e:
        return f"Error: {e}"
