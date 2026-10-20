import datetime
import json
import os
import sys
from pathlib import Path
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw"
SILVER_DIR = ROOT / "data" / "silver"
QUARANTINE_DIR = ROOT / "data" / "quarantine"
OUTPUTS_DIR = ROOT / "outputs"


def setup_directories():
    """Ensure output and storage directories exist."""
    SILVER_DIR.mkdir(parents=True, exist_ok=True)
    QUARANTINE_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)


def load_raw_csv(filename: str) -> pd.DataFrame:
    """Read CSV as raw string with BOM protection."""
    path = RAW_DIR / filename
    if not path.exists():
        sys.exit(f"Source file not found: {path}")
    return pd.read_csv(path, dtype=str, encoding="utf-8-sig")


def quarantine_bad_rows(table_name: str, bad_df: pd.DataFrame, reason: str):
    """Save invalid rows into quarantine folder with rejection reason."""
    if bad_df.empty:
        return
    quarantine_file = QUARANTINE_DIR / f"{table_name}_quarantine.csv"
    bad_df = bad_df.copy()
    bad_df["quarantine_reason"] = reason
    bad_df["quarantined_at"] = datetime.datetime.now().isoformat()
    bad_df.to_csv(quarantine_file, mode="a", index=False, header=not quarantine_file.exists())


def clean_customers(df: pd.DataFrame, rule_stats: dict) -> pd.DataFrame:
    """Enforce 5-digit zip code formatting."""
    df = df.copy()
    df["customer_zip_code_prefix"] = df["customer_zip_code_prefix"].str.zfill(5)
    rule_stats["customers_clean"] = len(df)
    return df


def clean_sellers(df: pd.DataFrame, rule_stats: dict) -> pd.DataFrame:
    """Enforce 5-digit zip code formatting."""
    df = df.copy()
    df["seller_zip_code_prefix"] = df["seller_zip_code_prefix"].str.zfill(5)
    rule_stats["sellers_clean"] = len(df)
    return df


def clean_geolocation(df: pd.DataFrame, rule_stats: dict) -> pd.DataFrame:
    """Filter coordinates outside Brazilian boundary and remove duplicates."""
    df = df.copy()
    df["geolocation_zip_code_prefix"] = df["geolocation_zip_code_prefix"].str.zfill(5)
    df["geolocation_lat"] = pd.to_numeric(df["geolocation_lat"], errors="coerce")
    df["geolocation_lng"] = pd.to_numeric(df["geolocation_lng"], errors="coerce")

    # Brazilian bounding box roughly lat -33.75..5.27, lng -73.98..-34.79
    invalid_mask = (
        (df["geolocation_lat"] > 5.27)
        | (df["geolocation_lat"] < -33.75)
        | (df["geolocation_lng"] > -34.79)
        | (df["geolocation_lng"] < -73.98)
        | df["geolocation_lat"].isna()
        | df["geolocation_lng"].isna()
    )

    bad_rows = df[invalid_mask]
    quarantine_bad_rows("geolocation", bad_rows, "coordinates_outside_brazil")
    rule_stats["geolocation_quarantined"] = len(bad_rows)

    clean_df = df[~invalid_mask].drop_duplicates()
    rule_stats["geolocation_clean"] = len(clean_df)
    return clean_df


def clean_orders(df: pd.DataFrame, rule_stats: dict) -> pd.DataFrame:
    """Parse timestamps and detect chronological delivery anomalies."""
    df = df.copy()
    ts_cols = [
        "order_purchase_timestamp",
        "order_approved_at",
        "order_delivered_carrier_date",
        "order_delivered_customer_date",
        "order_estimated_delivery_date",
    ]
    for col in ts_cols:
        df[col] = pd.to_datetime(df[col], errors="coerce")

    # Delivered status without actual delivery date
    missing_delivered = (df["order_status"] == "delivered") & (df["order_delivered_customer_date"].isna())
    bad_rows = df[missing_delivered]
    quarantine_bad_rows("orders", bad_rows, "delivered_status_missing_date")
    rule_stats["orders_missing_delivery_date"] = len(bad_rows)

    clean_df = df[~missing_delivered]
    rule_stats["orders_clean"] = len(clean_df)
    return clean_df


def clean_order_items(df: pd.DataFrame, rule_stats: dict) -> pd.DataFrame:
    """Parse item pricing and shipping limits."""
    df = df.copy()
    df["order_item_id"] = pd.to_numeric(df["order_item_id"], errors="coerce").astype(int)
    df["price"] = pd.to_numeric(df["price"], errors="coerce")
    df["freight_value"] = pd.to_numeric(df["freight_value"], errors="coerce")
    df["shipping_limit_date"] = pd.to_datetime(df["shipping_limit_date"], errors="coerce")
    rule_stats["order_items_clean"] = len(df)
    return df


def clean_order_payments(df: pd.DataFrame, rule_stats: dict) -> pd.DataFrame:
    """Ensure positive payment values and quarantine zero-value anomalies."""
    df = df.copy()
    df["payment_sequential"] = pd.to_numeric(df["payment_sequential"], errors="coerce").astype(int)
    df["payment_installments"] = pd.to_numeric(df["payment_installments"], errors="coerce").astype(int)
    df["payment_value"] = pd.to_numeric(df["payment_value"], errors="coerce")

    # Quarantine zero payment anomalies
    zero_pay = df["payment_value"] <= 0
    bad_rows = df[zero_pay]
    quarantine_bad_rows("order_payments", bad_rows, "zero_or_negative_payment_value")
    rule_stats["payments_zero_value"] = len(bad_rows)

    clean_df = df[~zero_pay]
    rule_stats["order_payments_clean"] = len(clean_df)
    return clean_df


def clean_order_reviews(df: pd.DataFrame, rule_stats: dict) -> pd.DataFrame:
    """Parse review scores and timestamps."""
    df = df.copy()
    df["review_score"] = pd.to_numeric(df["review_score"], errors="coerce").astype(int)
    df["review_creation_date"] = pd.to_datetime(df["review_creation_date"], errors="coerce")
    df["review_answer_timestamp"] = pd.to_datetime(df["review_answer_timestamp"], errors="coerce")
    rule_stats["order_reviews_clean"] = len(df)
    return df


def clean_products(df: pd.DataFrame, rule_stats: dict) -> pd.DataFrame:
    """Impute missing category with 'unknown' and parse numeric dimensions."""
    df = df.copy()
    df["product_category_name"] = df["product_category_name"].fillna("unknown")
    num_cols = [
        "product_name_lenght",
        "product_description_lenght",
        "product_photos_qty",
        "product_weight_g",
        "product_length_cm",
        "product_height_cm",
        "product_width_cm",
    ]
    for col in num_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    rule_stats["products_clean"] = len(df)
    return df


def clean_category_translation(df: pd.DataFrame, rule_stats: dict) -> pd.DataFrame:
    """Pass-through translation mapping."""
    df = df.copy()
    rule_stats["category_translation_clean"] = len(df)
    return df


def main():
    setup_directories()
    rule_stats = {}
    print("[silver] Processing 9 tables through data quality gates...")

    cleaning_tasks = {
        "customers": ("olist_customers_dataset.csv", clean_customers),
        "sellers": ("olist_sellers_dataset.csv", clean_sellers),
        "geolocation": ("olist_geolocation_dataset.csv", clean_geolocation),
        "orders": ("olist_orders_dataset.csv", clean_orders),
        "order_items": ("olist_order_items_dataset.csv", clean_order_items),
        "order_payments": ("olist_order_payments_dataset.csv", clean_order_payments),
        "order_reviews": ("olist_order_reviews_dataset.csv", clean_order_reviews),
        "products": ("olist_products_dataset.csv", clean_products),
        "product_category_name_translation": (
            "product_category_name_translation.csv",
            clean_category_translation,
        ),
    }

    report_lines = [
        "# Silver Layer Quality & Transformation Report\n",
        f"- Generated At: {datetime.datetime.now().isoformat()}",
        "- Format: Apache Parquet (Clean) + CSV (Quarantined)\n",
        "| Table | Raw Rows | Quarantined Rows | Clean Silver Rows | Status |",
        "|---|---|---|---|---|",
    ]

    for table_name, (csv_name, clean_fn) in cleaning_tasks.items():
        raw_df = load_raw_csv(csv_name)
        raw_count = len(raw_df)

        clean_df = clean_fn(raw_df, rule_stats)
        clean_count = len(clean_df)
        quarantine_count = raw_count - clean_count

        # Save to Parquet format in data/silver/
        parquet_file = SILVER_DIR / f"{table_name}.parquet"
        clean_df.to_parquet(parquet_file, index=False)

        status = "PASS" if quarantine_count == 0 else "PASS + QUARANTINE"
        report_lines.append(
            f"| `{table_name}` | {raw_count:,} | {quarantine_count:,} | {clean_count:,} | **{status}** |"
        )
        print(f"  - {table_name:30s} -> {clean_count:,} clean rows ({status})")

    report_path = OUTPUTS_DIR / "dq_report.md"
    report_path.write_text("\n".join(report_lines), encoding="utf-8")
    print(f"\n[silver] Completed! Quality report saved to: {report_path}")


if __name__ == "__main__":
    main()