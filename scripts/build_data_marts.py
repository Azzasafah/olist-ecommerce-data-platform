import datetime
import sys
import time
from pathlib import Path
import pandas as pd
import psycopg

ROOT = Path(__file__).resolve().parent.parent
OUTPUTS_DIR = ROOT / "outputs"
GOLD_DIR = ROOT / "data" / "gold"


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


def execute_marts_creation(conn):
    """Build business-level aggregate data marts answering Q1-Q4 plus financial reconciliation."""
    sql_script = """
    CREATE SCHEMA IF NOT EXISTS mart;

    -- Mart 1 (Q1: Monthly Revenue & Category Breakdown)
    DROP TABLE IF EXISTS mart.mart_revenue_monthly CASCADE;
    CREATE TABLE mart.mart_revenue_monthly AS
    SELECT 
        TO_CHAR(o.purchase_date, 'YYYY-MM') AS year_month,
        p.product_category_name,
        COUNT(DISTINCT o.order_id) AS total_orders,
        COUNT(oi.order_item_id) AS total_items_sold,
        ROUND(SUM(oi.price)::NUMERIC, 2) AS total_product_revenue,
        ROUND(SUM(oi.freight_value)::NUMERIC, 2) AS total_freight_revenue,
        ROUND(SUM(oi.total_item_value)::NUMERIC, 2) AS total_gross_revenue
    FROM dw.fact_order o
    JOIN dw.fact_order_item oi ON o.order_id = oi.order_id
    JOIN dw.dim_product p ON oi.product_id = p.product_id
    WHERE o.order_status = 'delivered'
    GROUP BY TO_CHAR(o.purchase_date, 'YYYY-MM'), p.product_category_name;

    -- Mart 2 (Q2: Delivery Performance & Review Score Impact by State)
    DROP TABLE IF EXISTS mart.mart_delivery_by_state CASCADE;
    CREATE TABLE mart.mart_delivery_by_state AS
    SELECT 
        c.customer_state,
        COUNT(o.order_id) AS total_delivered_orders,
        SUM(CASE WHEN o.is_late THEN 1 ELSE 0 END) AS late_orders_count,
        ROUND(AVG(CASE WHEN o.is_late THEN 1.0 ELSE 0.0 END) * 100, 2) AS late_rate_pct,
        ROUND(AVG(o.delivery_days)::NUMERIC, 2) AS avg_delivery_days,
        ROUND(AVG(CASE WHEN o.is_late THEN r.review_score ELSE NULL END)::NUMERIC, 2) AS avg_score_when_late,
        ROUND(AVG(CASE WHEN NOT o.is_late THEN r.review_score ELSE NULL END)::NUMERIC, 2) AS avg_score_when_on_time
    FROM dw.fact_order o
    JOIN dw.dim_customer c ON o.customer_unique_id = c.customer_unique_id
    LEFT JOIN dw.fact_review r ON o.order_id = r.order_id
    WHERE o.order_status = 'delivered'
    GROUP BY c.customer_state;

    -- Mart 3 (Q3: Seller Performance & SLA Compliance)
    DROP TABLE IF EXISTS mart.mart_seller_performance CASCADE;
    CREATE TABLE mart.mart_seller_performance AS
    SELECT 
        s.seller_id,
        s.seller_state,
        COUNT(DISTINCT oi.order_id) AS total_orders_fulfilled,
        ROUND(SUM(oi.price)::NUMERIC, 2) AS total_sales_value,
        ROUND(AVG(r.review_score)::NUMERIC, 2) AS avg_seller_review_score,
        SUM(CASE WHEN o.is_late THEN 1 ELSE 0 END) AS late_deliveries_count
    FROM dw.dim_seller s
    JOIN dw.fact_order_item oi ON s.seller_id = oi.seller_id
    JOIN dw.fact_order o ON oi.order_id = o.order_id
    LEFT JOIN dw.fact_review r ON o.order_id = r.order_id
    GROUP BY s.seller_id, s.seller_state;

    -- Mart 4 (Q4: Customer Lifetime Value & Repeat Purchase Segment)
    DROP TABLE IF EXISTS mart.mart_customer_retention CASCADE;
    CREATE TABLE mart.mart_customer_retention AS
    SELECT 
        c.customer_unique_id,
        c.customer_state,
        COUNT(DISTINCT o.order_id) AS lifetime_orders,
        ROUND(SUM(oi.total_item_value)::NUMERIC, 2) AS lifetime_spend,
        MIN(o.purchase_date) AS first_order_date,
        MAX(o.purchase_date) AS last_order_date,
        CASE WHEN COUNT(DISTINCT o.order_id) > 1 THEN TRUE ELSE FALSE END AS is_repeat_customer
    FROM dw.dim_customer c
    JOIN dw.fact_order o ON c.customer_unique_id = o.customer_unique_id
    JOIN dw.fact_order_item oi ON o.order_id = oi.order_id
    WHERE o.order_status = 'delivered'
    GROUP BY c.customer_unique_id, c.customer_state;

    -- Mart 5 (Financial Reconciliation: Billed Item+Freight vs Payments Paid)
    DROP TABLE IF EXISTS mart.mart_finance_reconciliation CASCADE;
    CREATE TABLE mart.mart_finance_reconciliation AS
    WITH billed AS (
        SELECT order_id, ROUND(SUM(total_item_value)::NUMERIC, 2) AS total_billed
        FROM dw.fact_order_item
        GROUP BY order_id
    ),
    paid AS (
        SELECT order_id, ROUND(SUM(payment_value)::NUMERIC, 2) AS total_paid
        FROM raw.order_payments
        GROUP BY order_id
    )
    SELECT 
        o.order_id,
        o.order_status,
        COALESCE(b.total_billed, 0.00) AS total_billed,
        COALESCE(p.total_paid, 0.00) AS total_paid,
        ROUND((COALESCE(b.total_billed, 0.00) - COALESCE(p.total_paid, 0.00))::NUMERIC, 2) AS discrepancy,
        CASE 
            WHEN b.total_billed IS NULL THEN 'ORDER_WITHOUT_ITEMS'
            WHEN p.total_paid IS NULL THEN 'ORDER_WITHOUT_PAYMENTS'
            WHEN ABS(b.total_billed - p.total_paid) > 0.01 THEN 'VALUE_MISMATCH'
            ELSE 'BALANCED'
        END AS reconciliation_status
    FROM dw.fact_order o
    LEFT JOIN billed b ON o.order_id = b.order_id
    LEFT JOIN paid p ON o.order_id = p.order_id;
    """

    with conn.cursor() as cur:
        cur.execute(sql_script)
    conn.commit()


def export_gold_parquet(conn):
    """Export marts to local gold layer in Parquet format."""
    GOLD_DIR.mkdir(parents=True, exist_ok=True)
    marts = [
        "mart_revenue_monthly",
        "mart_delivery_by_state",
        "mart_seller_performance",
        "mart_customer_retention",
        "mart_finance_reconciliation",
    ]

    export_stats = []
    for mart in marts:
        query = f"SELECT * FROM mart.{mart};"
        df = pd.read_sql_query(query, conn)
        target_path = GOLD_DIR / f"{mart}.parquet"
        df.to_parquet(target_path, index=False)
        export_stats.append((mart, len(df), target_path.name))
        print(f"  - mart.{mart:30s} -> {len(df):,} rows exported to {target_path.name}")

    return export_stats


def main():
    start_time = time.time()
    conn = get_db_connection()
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

    print("[marts] Building business data marts in PostgreSQL schema 'mart'...")
    execute_marts_creation(conn)

    print("[marts] Exporting Gold Parquet datasets...")
    stats = export_gold_parquet(conn)
    conn.close()

    elapsed = round(time.time() - start_time, 2)

    # Generate outputs/marts_report.md
    report_file = OUTPUTS_DIR / "marts_report.md"
    lines = [
        "# Data Marts & Financial Reconciliation Report\n",
        f"- Build Timestamp: {datetime.datetime.now().isoformat()}",
        f"- Total Duration: {elapsed} seconds",
        "- Destination: PostgreSQL (`schema: mart`) + Parquet (`data/gold/`)\n",
        "| Mart Name | Business Question Addressed | Row Count | Gold Parquet File |",
        "|---|---|---|---|",
        f"| `mart.mart_revenue_monthly` | Q1: Monthly Revenue & Category Breakdown | {stats[0][1]:,} | `{stats[0][2]}` |",
        f"| `mart.mart_delivery_by_state` | Q2: Delivery Delays & Review Impact | {stats[1][1]:,} | `{stats[1][2]}` |",
        f"| `mart.mart_seller_performance` | Q3: Seller Compliance & SLA | {stats[2][1]:,} | `{stats[2][2]}` |",
        f"| `mart.mart_customer_retention` | Q4: Customer Lifetime Value & Repeats | {stats[3][1]:,} | `{stats[3][2]}` |",
        f"| `mart.mart_finance_reconciliation` | Financial Audit (Billed vs Paid) | {stats[4][1]:,} | `{stats[4][2]}` |",
        "\n**Status: PASS (All business questions answered, Gold layer generated)**",
    ]
    report_file.write_text("\n".join(lines), encoding="utf-8")
    print(f"\n[marts] Completed! Report saved to: {report_file}")


if __name__ == "__main__":
    main()
