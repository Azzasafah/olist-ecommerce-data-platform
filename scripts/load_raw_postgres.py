import datetime
import io
import sys
import time
from pathlib import Path
import pandas as pd
import psycopg

ROOT = Path(__file__).resolve().parent.parent
SILVER_DIR = ROOT / "data" / "silver"
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


def get_db_connection():
    """Establish connection to PostgreSQL container."""
    env = load_env_variables()
    port = int(env.get("POSTGRES_PORT", "5432"))
    user = env.get("POSTGRES_USER", "olist")
    password = env.get("POSTGRES_PASSWORD", "olist")
    dbname = env.get("POSTGRES_DB", "olist")

    return psycopg.connect(
        host="127.0.0.1",
        port=port,
        user=user,
        password=password,
        dbname=dbname,
        autocommit=False,
    )


def initialize_schemas(conn):
    """Ensure raw schema exists in PostgreSQL."""
    with conn.cursor() as cur:
        cur.execute("CREATE SCHEMA IF NOT EXISTS raw;")
    conn.commit()


def create_table_ddl(conn, table_name: str, df: pd.DataFrame):
    """Map Pandas/Parquet data types to PostgreSQL DDL."""
    type_map = {
        "object": "TEXT",
        "int64": "BIGINT",
        "int32": "INTEGER",
        "float64": "NUMERIC",
        "datetime64[ns]": "TIMESTAMP",
        "datetime64[ms]": "TIMESTAMP",
        "bool": "BOOLEAN",
    }

    columns_sql = []
    for col, dtype in df.dtypes.items():
        sql_type = type_map.get(str(dtype), "TEXT")
        columns_sql.append(f'"{col}" {sql_type}')

    ddl = f'CREATE TABLE IF NOT EXISTS raw."{table_name}" (\n    ' + ",\n    ".join(columns_sql) + "\n);"
    with conn.cursor() as cur:
        cur.execute(ddl)
    conn.commit()


def copy_dataframe_to_postgres(conn, table_name: str, df: pd.DataFrame) -> int:
    """Bulk load data using atomic TRUNCATE + COPY inside a single transaction."""
    buffer = io.StringIO()
    df.to_csv(buffer, index=False, header=False, na_rep="\\N")
    buffer.seek(0)

    cols = ", ".join([f'"{col}"' for col in df.columns])
    
    # Gunakan FORMAT csv agar pemisah koma dipahami oleh PostgreSQL
    copy_sql = f'COPY raw."{table_name}" ({cols}) FROM STDIN WITH (FORMAT csv, NULL \'\\N\');'

    with conn.cursor() as cur:
        # Atomic idempotency: bersihkan dulu sebelum load
        cur.execute(f'TRUNCATE TABLE raw."{table_name}";')
        with cur.copy(copy_sql) as copy:
            copy.write(buffer.getvalue())

    conn.commit()
    return len(df)



def main():
    conn = get_db_connection()
    initialize_schemas(conn)
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

    parquet_files = sorted(list(SILVER_DIR.glob("*.parquet")))
    if not parquet_files:
        sys.exit(f"No silver parquet files found in {SILVER_DIR}")

    print(f"[load] Loading {len(parquet_files)} tables into PostgreSQL schema 'raw'...")
    report_rows = []

    for p_file in parquet_files:
        table_name = p_file.stem
        start_time = time.time()

        df = pd.read_parquet(p_file)
        create_table_ddl(conn, table_name, df)
        loaded_rows = copy_dataframe_to_postgres(conn, table_name, df)
        elapsed_sec = round(time.time() - start_time, 2)

        print(f"  - raw.{table_name:30s} -> {loaded_rows:,} rows loaded in {elapsed_sec}s")
        report_rows.append((table_name, loaded_rows, elapsed_sec))

    conn.close()

    # Generate outputs/load_report.md
    report_file = OUTPUTS_DIR / "load_report.md"
    lines = [
        "# PostgreSQL Raw Schema Load Report\n",
        f"- Load Timestamp: {datetime.datetime.now().isoformat()}",
        "- Destination Database: PostgreSQL container (`schema: raw`)\n",
        "| Table Name | Loaded Rows | Duration (Seconds) | Status |",
        "|---|---|---|---|",
    ]
    for tbl, rows, dur in report_rows:
        lines.append(f'| `raw."{tbl}"` | {rows:,} | {dur}s | **SUCCESS** |')

    report_file.write_text("\n".join(lines), encoding="utf-8")
    print(f"\n[load] Completed! Report saved to: {report_file}")


if __name__ == "__main__":
    main()