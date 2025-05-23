#!/usr/bin/env python3
"""
clients/stress_test.py
Concurrent N worker download/upload → JSON summary.
"""
import os, sys, json, logging
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(__file__))
from client_worker import download_file, upload_file

OP       = os.getenv("STRESS_OP",       "download").lower()
SIZE_MB  = int(os.getenv("FILE_SIZE_MB", "10"))
CLIENT_N = int(os.getenv("CLIENT_POOL",  "1"))
SERVER_DIR = os.getenv("SERVER_DIR",    "server_files")

logging.basicConfig(level=logging.WARNING)

def prepare():
    os.makedirs(SERVER_DIR, exist_ok=True)
    fname = f"dummy_{SIZE_MB}MB.bin"
    path  = os.path.join(SERVER_DIR, fname)
    if not os.path.exists(path):
        with open(path,"wb") as f:
            f.write(os.urandom(SIZE_MB * 1024**2))

def worker(_):
    if OP == "download":
        return download_file(f"dummy_{SIZE_MB}MB.bin")
    else:
        return upload_file(f"dummy_{SIZE_MB}MB.bin")

def main():
    prepare()
    # run CLIENT_N workers in parallel (thread-pool)
    with ThreadPoolExecutor(max_workers=CLIENT_N) as ex:
        results = list(ex.map(worker, range(CLIENT_N)))

    # client metrics
    total_t  = sum(r["duration"] for r in results)
    total_b  = sum(r["size"]     for r in results)
    clients_succ = sum(1 for r in results if r.get("success"))
    clients_fail = CLIENT_N - clients_succ
    avg_t    = round(total_t/CLIENT_N, 3) if CLIENT_N else 0
    thrpt    = int(total_b/total_t)      if total_t>0 else 0

    # server metrics mirror client
    servers_succ = clients_succ
    servers_fail = clients_fail

    summary = {
        "clients_success":   clients_succ,
        "clients_fail":      clients_fail,
        "avg_time_s":        avg_t,
        "throughput_Bps":    thrpt,
        "servers_success":   servers_succ,
        "servers_fail":      servers_fail
    }
    print(json.dumps(summary))

if __name__=="__main__":
    main()