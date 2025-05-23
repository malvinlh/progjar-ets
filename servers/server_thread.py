#!/usr/bin/env python3
"""
servers/server_thread.py
Multithread server: LIST/GET/PUT via ThreadPoolExecutor.
"""
import os
import socket
import logging
import signal
from concurrent.futures import ThreadPoolExecutor
from threading import Lock

HOST         = os.getenv("SERVER_HOST", "0.0.0.0")
PORT         = int(os.getenv("SERVER_PORT", "6667"))
SERVER_DIR   = os.getenv("SERVER_DIR", "server_files")
THREAD_COUNT = int(os.getenv("SERVER_THREAD", "5"))
BACKLOG      = THREAD_COUNT * 2
DELIM, BUF   = b"\r\n\r\n", 1 << 20

logger = logging.getLogger("srv_thread")
logger.setLevel(logging.INFO)
fmt = "%(asctime)s [%(threadName)s] %(levelname)s %(message)s"
ch = logging.StreamHandler()
ch.setFormatter(logging.Formatter(fmt))
logger.addHandler(ch)

_lock = Lock()

def handle_conn(conn, addr):
    start = __import__("time").perf_counter()
    try:
        buf = b""
        while DELIM not in buf:
            chunk = conn.recv(BUF)
            if not chunk:
                break
            buf += chunk

        raw, _ = buf.split(DELIM, 1)
        parts  = raw.decode().split(" ", 2)
        cmd    = parts[0].upper()
        fname  = parts[1] if len(parts)>1 else ""

        from file_protocol import FileProtocol
        fp = FileProtocol()

        if cmd == "LIST":
            resp = {"status":"OK", "data": os.listdir(SERVER_DIR)}
        elif cmd == "GET" and fname:
            resp = {"status":"OK", "data": fp.read_base64(os.path.join(SERVER_DIR, fname))}
        elif cmd == "PUT" and fname:
            fp.write_base64(os.path.join(SERVER_DIR, fname), parts[2])
            resp = {"status":"OK", "data":"uploaded"}
        else:
            resp = {"status":"ERROR","data":"invalid"}

        conn.sendall(fp.to_json(resp).encode() + DELIM)

        elapsed = __import__("time").perf_counter() - start
        with _lock:
            logger.info(f"{cmd} {fname} → {resp['status']} in {elapsed:.2f}s")
    except Exception:
        with _lock:
            logger.exception("handler exception")
    finally:
        conn.close()

def shutdown(sig, _):
    logger.info("Stopping thread server…")
    os._exit(0)

def main():
    os.makedirs(SERVER_DIR, exist_ok=True)
    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind((HOST, PORT))
    srv.listen(BACKLOG)
    logger.info(f"Thread-server @ {HOST}:{PORT}, pool={THREAD_COUNT}")

    with ThreadPoolExecutor(max_workers=THREAD_COUNT) as pool:
        while True:
            conn, addr = srv.accept()
            pool.submit(handle_conn, conn, addr)

if __name__ == "__main__":
    main()