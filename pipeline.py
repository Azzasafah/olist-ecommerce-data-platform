#!/usr/bin/env python3
"""pipeline.py — satu pintu untuk Olist Data Platform (starter Tugas Besar).

Yang SUDAH ada: init / up / down (infrastruktur, sama dengan lab Pertemuan 9).
Yang KAMU tulis: check, profile, bronze, silver, load, stream, model, marts, inject, report.
Tiap sub-perintah di bawah hanya menjelaskan targetnya lalu berhenti — ganti badannya dengan panggilan ke modulmu.

    python pipeline.py init && python pipeline.py up
    python pipeline.py check
    ...
"""

from sqlalchemy import true

import argparse
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SERVICES = ["postgres", "kafka", "minio", "kafka-ui", "jupyter"]


def read_env() -> dict[str, str]:
    env = {}
    p = ROOT / ".env"
    if p.exists():
        for line in p.read_text(encoding="utf-8").splitlines():
            if line.strip() and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip()
    return env


def compose(*args):
    return subprocess.run(["docker", "compose", *args], cwd=ROOT, check=True)


def port_free(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.3)
        return s.connect_ex(("127.0.0.1", port)) != 0


def cmd_init(a):
    if not (ROOT / ".env").exists():
        shutil.copy(ROOT / ".env.example", ROOT / ".env")
        print("[1] .env dibuat dari .env.example")
    e = read_env()
    print("[2] port:")
    for k, key in [("postgres", "POSTGRES_PORT"), ("kafka", "KAFKA_HOST_PORT"), ("kafka-ui", "KAFKA_UI_PORT"), ("minio", "MINIO_API_PORT"), ("jupyter", "JUPYTER_PORT")]:
        p = int(e.get(key, 0))
        print(f"    {k:10s} {p:6d}  {'bebas' if port_free(p) else 'BENTROK — ganti di .env (atau stack sudah jalan)'}")
    raw = ROOT / e.get("RAW_DIR", "data/raw")
    print(f"[3] data mentah: {raw} → {'ada' if any(raw.glob('*.csv')) else 'BELUM ADA — unduh dataset Kaggle ke sini, lalu python scripts/check_dataset.py'}")
    print("[4] TODO kamu: buat skema (sql/00_schemas.sql), topic Kafka, dan pastikan bucket MinIO ada")


def cmd_up(a):
    compose("up", "-d", *([] if a.build else ["--no-build"]))
    t0 = time.time()
    seen = {}
    while time.time() - t0 < 240 and len(seen) < len(SERVICES):
        for svc in SERVICES:
            if svc in seen:
                continue
            r = subprocess.run(["docker", "inspect", f"olist-{svc}", "--format", "{{.State.Health.Status}}"], capture_output=True, text=True)
            if r.returncode == 0 and r.stdout.strip() == "healthy":
                seen[svc] = round(time.time() - t0, 1)
                print(f"    {svc:10s} healthy pada {seen[svc]} s")
        time.sleep(1)
    missing = [s for s in SERVICES if s not in seen]
    if missing:
        sys.exit(f"TIMEOUT: belum healthy: {missing} — cek `docker compose ps` dan `docker compose logs <svc>`")

def cmd_down(a):
    compose("down", *(["-v"] if a.volumes else []))


def cmd_check(a):
    out_file = ROOT / "outputs" / "dataset_check.md"
    out_file.parent.mkdir(parents=True, exist_ok=True)
    cmd = [sys.executable, str(ROOT / "scripts" / "check_dataset.py")]
    res = subprocess.run(cmd, capture_output=True, text=True)
    print(res.stdout)
    if res.stderr:
        print(res.stderr, file=sys.stderr)
    out_file.write_text(f"# Dataset Check Report\n\n```text\n{res.stdout}\n```\n", encoding="utf-8")
    print(f"[check] Laporan disimpan ke {out_file}")
    if res.returncode != 0:
        sys.exit(res.returncode)


def cmd_profile(a):
    out_file = ROOT / "outputs" / "profile.md"
    out_file.parent.mkdir(parents=True, exist_ok=True)
    cmd = [sys.executable, str(ROOT / "scripts" / "profile_dataset.py")]
    res = subprocess.run(cmd, capture_output=True, text=True)
    print(res.stdout)
    if res.stderr:
        print(res.stderr, file=sys.stderr)
    if res.returncode != 0:
        sys.exit(res.returncode)

def cmd_bronze(a):
    cmd = [sys.executable, str(ROOT / "scripts" / "ingest_bronze.py")]
    res = subprocess.run(cmd, capture_output=True, text=True)
    print(res.stdout)
    if res.stderr:
        print(res.stderr, file=sys.stderr)
    if res.returncode != 0:
        sys.exit(res.returncode)

def cmd_silver(a):
    cmd = [sys.executable, str(ROOT / "scripts" / "process_silver.py")]
    res = subprocess.run(cmd, capture_output=True, text=True)
    print(res.stdout)
    if res.stderr:
        print(res.stderr, file=sys.stderr)
    if res.returncode != 0:
        sys.exit(res.returncode)

def cmd_load(a):
    cmd = [sys.executable, str(ROOT / "scripts" / "load_raw_postgres.py")]
    res = subprocess.run(cmd, capture_output=True, text=True)
    print(res.stdout)
    if res.stderr:
        print(res.stderr, file=sys.stderr)
    if res.returncode != 0:
        sys.exit(res.returncode)

def cmd_stream(a):
    cmd = [sys.executable, str(ROOT / "scripts" / "stream_pipeline.py")]
    res = subprocess.run(cmd, capture_output=True, text=True)
    print(res.stdout)
    if res.stderr:
        print(res.stderr, file=sys.stderr)
    if res.returncode != 0:
        sys.exit(res.returncode)

def cmd_model(a):
    cmd = [sys.executable, str(ROOT / "scripts" / "build_data_warehouse.py")]
    res = subprocess.run(cmd, capture_output=True, text=True)
    print(res.stdout)
    if res.stderr:
        print(res.stderr, file=sys.stderr)
    if res.returncode != 0:
        sys.exit(res.returncode)

def cmd_marts(a):
    cmd = [sys.executable, str(ROOT / "scripts" / "build_data_marts.py")]
    res = subprocess.run(cmd, capture_output=True, text=True)
    print(res.stdout)
    if res.stderr:
        print(res.stderr, file=sys.stderr)
    if res.returncode != 0:
        sys.exit(res.returncode)

def todo(stage: str, target: str):
    def fn(a):
        print(f"[{stage}] belum diimplementasikan.\n  Target: {target}\n  Lihat TUGAS_BESAR.md bagian {stage}.")
        sys.exit(2)
    return fn


PARSER = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
SUB = PARSER.add_subparsers(dest="cmd", required=True)
p = SUB.add_parser("init"); p.set_defaults(func=cmd_init)
p = SUB.add_parser("up"); p.add_argument("--build", action="store_true", help="bangun image jupyter (pertama kali)"); p.set_defaults(func=cmd_up)
p = SUB.add_parser("down"); p.add_argument("-v", "--volumes", action="store_true"); p.set_defaults(func=cmd_down)

p = SUB.add_parser("check"); p.set_defaults(func=cmd_check)
p = SUB.add_parser("profile"); p.set_defaults(func=cmd_profile)
p = SUB.add_parser("bronze"); p.set_defaults(func=cmd_bronze)
p = SUB.add_parser("silver"); p.set_defaults(func=cmd_silver)
p = SUB.add_parser("load"); p.set_defaults(func=cmd_load)
p = SUB.add_parser("stream"); p.set_defaults(func=cmd_stream)
p = SUB.add_parser("model"); p.set_defaults(func=cmd_model)
p = SUB.add_parser("marts"); p.set_defaults(func=cmd_marts)

for name, stage, target in [
    ("inject", "T6", "≥ 5 failure injection yang pulih sendiri → outputs/failure_tests.md"),
    ("report", "T6", "EVALUATION_EVIDENCE.md dari outputs/*.json"),
]:
    p = SUB.add_parser(name); p.set_defaults(func=todo(stage, target))

if __name__ == "__main__":
    args = PARSER.parse_args()
    args.func(args)

