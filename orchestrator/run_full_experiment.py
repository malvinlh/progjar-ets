#!/usr/bin/env python3
"""
orchestrator/run_full_experiment.py
Loop 108 kombinasi → results.csv + print OK/FAIL
"""
import os, csv, time, subprocess, logging, json, signal

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__),".."))
SCRIPTS = {
    "thread":  os.path.join(PROJECT_ROOT,"servers","server_thread.py"),
    "process": os.path.join(PROJECT_ROOT,"servers","server_mproc.py")
}
STRESS   = os.path.join(PROJECT_ROOT,"clients","stress_test.py")
CSV_FILE = os.path.join(PROJECT_ROOT,"results.csv")

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")

FIELDS = [
    "No","server_mode","server_workers",
    "client_workers","operation","size_mb",
    "avg_time_s","throughput_Bps",
    "clients_success","clients_fail",
    "servers_success","servers_fail"
]

def init_csv():
    if not os.path.exists(CSV_FILE) or os.path.getsize(CSV_FILE)==0:
        with open(CSV_FILE,"w", newline="") as f:
            csv.DictWriter(f, fieldnames=FIELDS).writeheader()

def start_server(mode, workers):
    env = os.environ.copy()
    env["SERVER_DIR"] = os.path.join(PROJECT_ROOT,"server_files")
    # set jumlah worker sesuai mode
    key = "SERVER_THREAD" if mode=="thread" else "SERVER_PROC"
    env[key] = str(workers)
    # jalankan server di process group baru
    return subprocess.Popen(
        ["python3", SCRIPTS[mode]],
        cwd=PROJECT_ROOT,
        preexec_fn=os.setsid,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )

def stop_server(p):
    os.killpg(os.getpgid(p.pid), signal.SIGTERM)

def run_test(op, size, pool):
    env = os.environ.copy()
    env.update({
        "STRESS_OP":    op,
        "FILE_SIZE_MB": str(size),
        "CLIENT_POOL":  str(pool),
        "SERVER_DIR":   os.path.join(PROJECT_ROOT,"server_files")
    })
    try:
        proc = subprocess.run(
            ["python3", STRESS],
            cwd=PROJECT_ROOT,
            capture_output=True, text=True,
            env=env
        )
        return json.loads(proc.stdout)
    except Exception as e:
        logging.error(f"stress_test error: {e}")
        # fallback zero metrics
        return {
            "clients_success":   0,
            "clients_fail":      pool,
            "avg_time_s":        0,
            "throughput_Bps":    0,
            "servers_success":   0,
            "servers_fail":      pool
        }

def main():
    init_csv()
    idx = 1

    for mode in ("thread","process"):
        for sw in (1,5,50):
            logging.info(f"→ start server: {mode} ({sw} workers)")
            srv = start_server(mode, sw)
            time.sleep(2)  # beri waktu server up

            for cw in (1,5,50):
                for op in ("download","upload"):
                    for sz in (10,50,100):
                        logging.info(f"[{idx}] {mode}/{sw} | cli={cw} | {op} {sz}MB")
                        res = run_test(op, sz, cw)

                        row = {
                            "No":               idx,
                            "server_mode":      mode,
                            "server_workers":   sw,
                            "client_workers":   cw,
                            "operation":        op,
                            "size_mb":          sz,
                            "avg_time_s":       res["avg_time_s"],
                            "throughput_Bps":   res["throughput_Bps"],
                            "clients_success":  res["clients_success"],
                            "clients_fail":     res["clients_fail"],
                            "servers_success":  res["servers_success"],
                            "servers_fail":     res["servers_fail"]
                        }
                        with open(CSV_FILE,"a", newline="") as f:
                            csv.DictWriter(f, fieldnames=FIELDS).writerow(row)

                        cs = "OK" if res["clients_fail"]==0 else "FAIL"
                        ps = "OK" if res["servers_fail"]==0 else "FAIL"
                        print(f"[{idx}] server: {ps}  |  client: {cs}")

                        idx += 1

            logging.info(f"← stop server: {mode} ({sw})")
            stop_server(srv)
            time.sleep(1)

    logging.info(f"Done: {idx-1} runs, see {CSV_FILE}")

if __name__=="__main__":
    main()