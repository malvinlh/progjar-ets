#!/usr/bin/env python3
"""
clients/client_worker.py
LIST/GET/PUT lewat socket; upload baca langsung dari SERVER_DIR.
"""
import os
import socket
import json
import base64
import time
import logging

HOST           = os.getenv("CLIENT_HOST", "127.0.0.1")
PORT           = int(os.getenv("CLIENT_PORT", "6667"))
DELIM, BUF     = b"\r\n\r\n", 1 << 20
TIMEOUT        = int(os.getenv("CLIENT_TIMEOUT", "300"))
RETRIES        = int(os.getenv("CLIENT_RETRY", "2"))

logger = logging.getLogger("clt_worker")
logger.setLevel(logging.INFO)
h = logging.StreamHandler()
h.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
logger.addHandler(h)

def send_cmd(cmd: str) -> dict:
    """Kirim perintah ke server (LIST/GET/PUT), retry hingga RETRIES."""
    for attempt in range(1, RETRIES + 1):
        try:
            with socket.create_connection((HOST, PORT), timeout=TIMEOUT) as s:
                s.sendall(cmd.encode() + DELIM)
                data = b""
                while DELIM not in data:
                    chunk = s.recv(BUF)
                    if not chunk:
                        break
                    data += chunk
            raw, _ = data.split(DELIM, 1)
            return json.loads(raw.decode())
        except Exception as e:
            logger.warning(f"[send_cmd] attempt {attempt} failed: {e}")
            if attempt == RETRIES:
                return {"status": "ERROR", "data": str(e)}

def list_files() -> dict:
    """
    Minta daftar file di server.
    Returns:
      {"success": bool, "files": [str,...], "error": str (jika gagal)}
    """
    resp = send_cmd("LIST")
    if resp.get("status") != "OK":
        return {"success": False, "files": [], "error": resp.get("data")}
    return {"success": True, "files": resp.get("data", [])}

def download_file(fname: str) -> dict:
    """
    Download file dari server menjadi 'client_<fname>'.
    Returns:
      {"success": bool, "duration": float, "size": int}
    """
    start = time.perf_counter()
    resp = send_cmd(f"GET {fname}")
    duration = time.perf_counter() - start

    if resp.get("status") != "OK":
        return {"success": False, "duration": duration, "size": 0}

    raw = base64.b64decode(resp["data"])
    out = f"client_{fname}"
    with open(out, "wb") as f:
        f.write(raw)

    size = len(raw)
    logger.info(f"Downloaded {fname} ({size} B) in {duration:.2f}s")
    return {"success": True, "duration": duration, "size": size}

def upload_file(fname: str) -> dict:
    """
    Upload file dari SERVER_DIR ke server.
    'fname' adalah basename file di SERVER_DIR.
    Returns:
      {"success": bool, "duration": float, "size": int}
    """
    server_dir = os.getenv("SERVER_DIR", "server_files")
    full_path  = os.path.join(server_dir, fname)
    if not os.path.isfile(full_path):
        return {"success": False, "duration": 0, "size": 0}

    raw = open(full_path, "rb").read()
    b64 = base64.b64encode(raw).decode()
    start = time.perf_counter()
    resp = send_cmd(f"PUT {fname} {b64}")
    duration = time.perf_counter() - start

    if resp.get("status") != "OK":
        return {"success": False, "duration": duration, "size": 0}

    size = len(raw)
    logger.info(f"Uploaded {fname} ({size} B) in {duration:.2f}s")
    return {"success": True, "duration": duration, "size": size}