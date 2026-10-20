import datetime
import sys
import time
from pathlib import Path
import psycopg

ROOT = Path(__file__).resolve().parent.parent
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
    """Connect to PostgreSQL container."""
    env = load_env_variables()
    port = int(env.get("POSTGRES_PORT", "5432"))
    user = env.get("POSTGRES_USER", "olist")
    password = env.get("POSTGRES_PASSWORD", "olist")
    dbname = env.get("POSTGRES_DB", "olist")

    return psycopg.connect(
        host="localhost",
        port=port,
        user=user,
        password=password,
        dbname=dbname,
        sslmode="disable",
        autocommit=False,
    )


def execute_sql_ddl_and_dml(conn):
    """Create dimensions and fact tables using pure idempotent SQL transforms."""
    sql_script = """
    CREATE SCHEMA IF NOT EXISTS dw;

    -- 1. Dimension: dim_customer (Grain: customer_unique_id)
    DROP TABLE IF EXISTS dw.dim_customer CASCADE;
    CREATE TABLE dw.dim_customer AS
    SELECT DISTINCT ON (customer_unique_id)
        customer_unique_id,
        customer_id AS sample_customer_id,
        customer_zip_code_prefix,
        customer_city,
        customer_state
    FROM raw.customers
    ORDER BY customer_unique_id, customer_id;
    ALTER TABLE dw.dim_customer ADD PRIMARY KEY (customer_unique_id);

    -- 2. Dimension: dim_seller
    DROP TABLE IF EXISTS dw.dim_seller CASCADE;
    CREATE TABLE dw.dim_seller AS
    SELECT 
        seller_id,
        seller_zip_code_prefix,
        seller_city,
        seller_state
    FROM raw.sellers;
    ALTER TABLE dw.dim_seller ADD PRIMARY KEY (seller_id);

    -- 3. Dimension: dim_product (with English Category Translation)
    DROP TABLE IF EXISTS dw.dim_product CASCADE;
    CREATE TABLE dw.dim_product AS
    SELECT 
        p.product_id,
        COALESCE(t.product_category_name_english, p.product_category_name, 'unknown') AS product_category_name,
        p.product_weight_g,
        p.product_length_cm,
        p.product_height_cm,
        p.product_width_cm
    FROM raw.products p
    LEFT JOIN raw.product_category_name_translation t 
        ON p.product_category_name = t.product_category_name;
    ALTER TABLE dw.dim_product ADD PRIMARY KEY (product_id);

    -- 4. Dimension: dim_date
    DROP TABLE IF EXISTS dw.dim_date CASCADE;
    CREATE TABLE dw.dim_date AS
    SELECT 
        d::DATE AS date_id,
        EXTRACT(YEAR FROM d)::INT AS year,
        EXTRACT(MONTH FROM d)::INT AS month,
        EXTRACT(DAY FROM d)::INT AS day,
        TO_CHAR(d, 'Month') AS month_name,
        EXTRACT(QUARTER FROM d)::INT AS quarter,
        EXTRACT(ISODOW FROM d)::INT AS day_of_week
    FROM GENERATE_SERIES('2016-01-01'::DATE, '2019-12-31'::DATE, '1 day'::INTERVAL) d;
    ALTER TABLE dw.dim_date ADD PRIMARY KEY (date_id);

    -- 5. Fact Table: fact_order
    DROP TABLE IF EXISTS dw.fact_order CASCADE;
    CREATE TABLE dw.fact_order AS
    SELECT 
        o.order_id,
        c.customer_unique_id,
        o.order_status,
        o.order_purchase_timestamp::DATE AS purchase_date,
        o.order_purchase_timestamp,
        o.order_approved_at,
        o.order_delivered_carrier_date,
        o.order_delivered_customer_date,
        o.order_estimated_delivery_date,
        CASE 
            WHEN o.order_delivered_customer_date > o.order_estimated_delivery_date THEN TRUE 
            ELSE FALSE 
        END AS is_late,
        ROUND(EXTRACT(EPOCH FROM (o.order_delivered_customer_date - o.order_purchase_timestamp)) / 86400.0, 2) AS delivery_days
    FROM raw.orders o
    LEFT JOIN raw.customers c ON o.customer_id = c.customer_id;
    ALTER TABLE dw.fact_order ADD PRIMARY KEY (order_id);

    -- 6. Fact Table: fact_order_item
    DROP TABLE IF EXISTS dw.fact_order_item CASCADE;
    CREATE TABLE dw.fact_order_item AS
    SELECT 
        oi.order_id,
        oi.order_item_id,
        oi.product_id,
        oi.seller_id,
        oi.shipping_limit_date,
        oi.price,
        oi.freight_value,
        ROUND((oi.price + oi.freight_value)::NUMERIC, 2) AS total_item_value
    FROM raw.order_items oi;
    ALTER TABLE dw.fact_order_item ADD PRIMARY KEY (order_id, order_item_id);

    -- 7. Fact Table: fact_review (Deduplicated choosing latest review timestamp)
    DROP TABLE IF EXISTS dw.fact_review CASCADE;
    CREATE TABLE dw.fact_review AS
    SELECT DISTINCT ON (order_id)
        order_id,
        review_id,
        review_score,
        review_creation_date,
        review_answer_timestamp
    FROM raw.order_reviews
    ORDER BY order_id, review_answer_timestamp DESC;
    ALTER TABLE dw.fact_review ADD PRIMARY KEY (order_id);
    """

    with conn.cursor() as cur:
        cur.execute(sql_script)
    conn.commit()


def main():
    start_time = time.time()
    conn = get_db_connection()
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

    print("[model] Building Star Schema tables in PostgreSQL schema 'dw'...")
    execute_sql_ddl_and_dml(conn)

    tables_to_count = [
        "dim_customer",
        "dim_seller",
        "dim_product",
        "dim_date",
        "fact_order",
        "fact_order_item",
        "fact_review",
    ]

    report_rows = []
    with conn.cursor() as cur:
        for tbl in tables_to_count:
            cur.execute(f"SELECT COUNT(*) FROM dw.{tbl};")
            count = cur.fetchone()[0]
            print(f"  - dw.{tbl:20s} -> {count:,} rows")
            report_rows.append((tbl, count))

    conn.close()
    elapsed = round(time.time() - start_time, 2)

    # Generate outputs/dw_report.md
    report_file = OUTPUTS_DIR / "dw_report.md"
    lines = [
        "# Data Warehouse (Star Schema) Report\n",
        f"- Build Timestamp: {datetime.datetime.now().isoformat()}",
        f"- Total Duration: {elapsed} seconds",
        "- Architecture: Kimball Star Schema (`schema: dw`)\n",
        "| Table Name | Role | Row Count | Primary Key |",
        "|---|---|---|---|",
        f"| `dw.dim_customer` | Dimension | {report_rows[0][1]:,} | `customer_unique_id` |",
        f"| `dw.dim_seller` | Dimension | {report_rows[1][1]:,} | `seller_id` |",
        f"| `dw.dim_product` | Dimension | {report_rows[2][1]:,} | `product_id` |",
        f"| `dw.dim_date` | Dimension | {report_rows[3][1]:,} | `date_id` |",
        f"| `dw.fact_order` | Fact | {report_rows[4][1]:,} | `order_id` |",
        f"| `dw.fact_order_item` | Fact | {report_rows[5][1]:,} | `(order_id, order_item_id)` |",
        f"| `dw.fact_review` | Fact | {report_rows[6][1]:,} | `order_id` |",
        "\n**Status: PASS (PK constraints verified, Star Schema modeled)**",
    ]
    report_file.write_text("\n".join(lines), encoding="utf-8")
    print(f"\n[model] Completed! DW report saved to: {report_file}")


if __name__ == "__main__":
    main()
