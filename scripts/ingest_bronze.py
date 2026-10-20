import csv
import datetime
import hashlib
import json
import sys
from pathlib import Path
import boto3
from botocore.client import Config

# Project directories
ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw"
OUTPUTS_DIR = ROOT / "outputs"


def load_env_variables() -> dict:
    """Read configuration from .env file."""
    env = {}
    env_file = ROOT / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, val = line.split("=", 1)
                env[key.strip()] = val.strip()
    return env


def create_s3_client():
    """Initialize MinIO S3 client using credentials from .env."""
    env = load_env_variables()
    port = env.get("MINIO_API_PORT", "9000")
    endpoint = f"http://127.0.0.1:{port}"
    user = env.get("MINIO_ROOT_USER", "minioadmin")
    password = env.get("MINIO_ROOT_PASSWORD", "minioadmin")

    return boto3.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=user,
        aws_secret_access_key=password,
        config=Config(signature_version="s3v4"),
        region_name="us-east-1",
    )


def compute_file_md5(file_path: Path) -> str:
    """Calculate MD5 checksum to detect file content changes."""
    hasher = hashlib.md5()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def count_csv_rows(file_path: Path) -> int:
    """Count data rows safely handling multiline fields."""
    csv.field_size_limit(1 << 30)
    with open(file_path, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.reader(f)
        next(reader, None)  # Skip header row
        return sum(1 for _ in reader)


def fetch_remote_manifest(s3_client, bucket: str, manifest_key: str) -> dict:
    """Retrieve existing table manifest from MinIO, or return empty template."""
    try:
        response = s3_client.get_object(Bucket=bucket, Key=manifest_key)
        return json.loads(response["Body"].read().decode("utf-8"))
    except Exception:
        return {"versions": []}


def save_remote_manifest(s3_client, bucket: str, manifest_key: str, manifest: dict):
    """Upload updated manifest JSON to MinIO."""
    s3_client.put_object(
        Bucket=bucket,
        Key=manifest_key,
        Body=json.dumps(manifest, indent=2).encode("utf-8"),
        ContentType="application/json",
    )


def ingest_single_file(s3_client, bucket: str, file_path: Path) -> dict:
    """Ingest one CSV file into MinIO with idempotency check."""
    table_name = file_path.stem.replace("olist_", "").replace("_dataset", "")
    current_md5 = compute_file_md5(file_path)
    file_size = file_path.stat().st_size
    manifest_key = f"olist/{table_name}/manifest.json"

    # Step 1: Check existing manifest for idempotency
    manifest = fetch_remote_manifest(s3_client, bucket, manifest_key)
    manifest["table"] = table_name

    last_version = manifest["versions"][-1] if manifest["versions"] else None
    if last_version and last_version.get("md5") == current_md5:
        # File has not changed: do not re-upload
        return {
            "table": table_name,
            "status": "unchanged",
            "rows": last_version["row_count"],
            "size": file_size,
            "key": last_version["object_key"],
        }

    # Step 2: File is new or modified: upload new version
    version_number = len(manifest["versions"]) + 1
    status = "uploaded" if version_number == 1 else "new_version"
    today = datetime.date.today().isoformat()
    object_key = f"olist/{table_name}/ingest_date={today}/v{version_number}_{file_path.name}"
    total_rows = count_csv_rows(file_path)

    s3_client.upload_file(str(file_path), bucket, object_key)

    # Step 3: Append version record and save manifest
    version_record = {
        "version": version_number,
        "md5": current_md5,
        "size_bytes": file_size,
        "row_count": total_rows,
        "object_key": object_key,
        "ingested_at": datetime.datetime.now().isoformat(),
    }
    manifest["versions"].append(version_record)
    save_remote_manifest(s3_client, bucket, manifest_key, manifest)

    return {
        "table": table_name,
        "status": status,
        "rows": total_rows,
        "size": file_size,
        "key": object_key,
    }


def write_markdown_report(report_records: list):
    """Generate final Markdown report required by T1."""
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    report_file = OUTPUTS_DIR / "bronze_report.md"

    lines = [
        "# Bronze Ingestion Report\n",
        f"- Ingest Timestamp: {datetime.datetime.now().isoformat()}",
        "- Storage Destination: MinIO (`s3://bronze/olist/`)\n",
        "| Table | Status | Rows | Size (Bytes) | MinIO Object Key |",
        "|---|---|---|---|---|",
    ]

    for item in report_records:
        lines.append(
            f"| `{item['table']}` | **{item['status']}** | {item['rows']:,} | {item['size']:,} | `{item['key']}` |"
        )

    report_file.write_text("\n".join(lines), encoding="utf-8")
    print(f"\n[bronze] Report generated at: {report_file}")


def main():
    s3_client = create_s3_client()
    bucket_name = "bronze"

    # Ensure bronze bucket exists
    try:
        s3_client.head_bucket(Bucket=bucket_name)
    except Exception:
        s3_client.create_bucket(Bucket=bucket_name)

    csv_files = sorted(list(RAW_DIR.glob("*.csv")))
    if not csv_files:
        sys.exit(f"No CSV files found in {RAW_DIR}")

    print(f"[bronze] Ingesting {len(csv_files)} files into bucket '{bucket_name}'...")
    results = []

    for file_path in csv_files:
        result = ingest_single_file(s3_client, bucket_name, file_path)
        print(f"  - {result['table']:25s} : {result['status'].upper()}")
        results.append(result)

    write_markdown_report(results)


if __name__ == "__main__":
    main()
