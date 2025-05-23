#!/usr/bin/env python3
"""
servers/server_mproc.py
Multiprocessing server dengan fixed-size pool:
spawn N worker process, masing-masing looping accept().
"""
import os
import socket
import logging
import signal
import sys

HOST       = os.getenv("SERVER_HOST", "0.0.0.0")
PORT       = int(os.getenv("SERVER_PORT", "6667"))
SERVER_DIR = os.getenv("SERVER_DIR", "server_files")
MAX_PROC   = int(os.getenv("SERVER_PROC", "4"))
BACKLOG    = MAX_PROC * 2
DELIM      = b"\r\n\r\n"
BUF_SIZE   = 1 << 20

logger = logging.getLogger("srv_mproc_pool")
logger.setLevel(logging.INFO)
fmt = "%(asctime)s [PID %(process)d] %(levelname)s %(message)s"
ch = logging.StreamHandler()
ch.setFormatter(logging.Formatter(fmt))
logger.addHandler(ch)

def handle_request(conn):
    try:
        data = b""
        while True:
            chunk = conn.recv(BUF_SIZE)
            if not chunk:
                break
            data += chunk
            if DELIM in data:
                break

        if DELIM not in data:
            logger.error("Malformed request (no delimiter)")
            return

        raw, _ = data.split(DELIM, 1)
        parts   = raw.decode().split(" ", 2)
        cmd     = parts[0].upper()
        fname   = parts[1] if len(parts)>1 else ""

        from file_protocol import FileProtocol
        fp = FileProtocol()

        if cmd == "LIST":
            result = {"status":"OK","data": os.listdir(SERVER_DIR)}
        elif cmd == "GET" and fname:
            result = {"status":"OK","data": fp.read_base64(os.path.join(SERVER_DIR, fname))}
        elif cmd == "PUT" and fname:
            fp.write_base64(os.path.join(SERVER_DIR, fname), parts[2])
            result = {"status":"OK","data":"uploaded"}
        else:
            result = {"status":"ERROR","data":"invalid command"}

        payload = fp.to_json(result).encode() + DELIM
        try:
            conn.sendall(payload)
        except BrokenPipeError:
            logger.warning("Client disconnected before sendall()")

        logger.info(f"Handled {cmd} {fname} → {result['status']}")
    except Exception:
        logger.exception("Exception in worker")
    finally:
        conn.close()

def worker_loop(listen_sock):
    while True:
        conn, _ = listen_sock.accept()
        handle_request(conn)

def main():
    os.makedirs(SERVER_DIR, exist_ok=True)

    def on_term(sig, frame):
        logger.info("Shutting down pool server…")
        sys.exit(0)
    signal.signal(signal.SIGINT, on_term)
    signal.signal(signal.SIGTERM, on_term)

    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind((HOST, PORT))
    srv.listen(BACKLOG)
    logger.info(f"Pool-MProc server @ {HOST}:{PORT} with {MAX_PROC} workers")

    # Pre-fork MAX_PROC processes
    for _ in range(MAX_PROC):
        pid = os.fork()
        if pid == 0:
            worker_loop(srv)
            os._exit(0)

    # Parent waits for children
    for _ in range(MAX_PROC):
        os.wait()

if __name__ == "__main__":
    main()