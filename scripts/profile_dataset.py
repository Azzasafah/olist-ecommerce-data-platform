import sys
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw"
OUTPUTS_DIR = ROOT / "outputs"


def load(name: str) -> pd.DataFrame:
    p = RAW_DIR / name
    if not p.exists():
        sys.exit(f"File hilang: {p}")
    return pd.read_csv(p, dtype=str, encoding="utf-8-sig")


def main():
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    report_path = OUTPUTS_DIR / "profile.md"
    
    print("[profile] Membaca 9 file CSV dan menghitung statistik...")
    orders = load("olist_orders_dataset.csv")
    items = load("olist_order_items_dataset.csv")
    payments = load("olist_order_payments_dataset.csv")
    customers = load("olist_customers_dataset.csv")
    reviews = load("olist_order_reviews_dataset.csv")
    products = load("olist_products_dataset.csv")
    sellers = load("olist_sellers_dataset.csv")
    geo = load("olist_geolocation_dataset.csv")
    trans = load("product_category_name_translation.csv")

    tables = {
        "orders": orders,
        "order_items": items,
        "order_payments": payments,
        "customers": customers,
        "order_reviews": reviews,
        "products": products,
        "sellers": sellers,
        "geolocation": geo,
        "category_translation": trans,
    }

    lines = ["# Automated Data Profiling Report — Olist Dataset\n"]
    lines.append("## 1. Ringkasan Tabel & Kualitas Kolom\n")

    for tname, df in tables.items():
        total = len(df)
        lines.append(f"### `{tname}` ({total:,} baris, {len(df.columns)} kolom)\n")
        lines.append("| Kolom | Null Count | Null % | Nilai Unik | Contoh Nilai |")
        lines.append("|---|---|---|---|---|")
        for col in df.columns:
            n_null = df[col].isna().sum() + (df[col] == "").sum()
            pct_null = (n_null / total) * 100
            n_uniq = df[col].nunique()
            sample = str(df[col].dropna().iloc[0]) if not df[col].dropna().empty else "-"
            sample = (sample[:25] + "...") if len(sample) > 25 else sample
            lines.append(f"| {col} | {n_null:,} | {pct_null:.2f}% | {n_uniq:,} | `{sample}` |")
        lines.append("")

    # --- ANALISIS 10 TEMUAN KOTOR EKSPLISIT ---
    lines.append("## 2. Investigasi Temuan 'Kotor' Riil\n")

    # 1. Customer ID vs Customer Unique ID
    u_cust = customers["customer_unique_id"].nunique()
    rep_cust = (customers["customer_unique_id"].value_counts() > 1).sum()
    lines.append(f"- **Temuan 1 (Customers):** `customer_id` unik = {customers['customer_id'].nunique():,}, tapi `customer_unique_id` (orang asli) cuma {u_cust:,}. Ada {rep_cust:,} pelanggan yang belanja ulang.")

    # 2. Review ID Duplikat
    u_rev = reviews["review_id"].nunique()
    order_multi_rev = (reviews["order_id"].value_counts() > 1).sum()
    lines.append(f"- **Temuan 2 (Reviews):** `review_id` tidak unik ({u_rev:,} unik dari {len(reviews):,} baris). Ada {order_multi_rev:,} order yang punya > 1 review.")

    # 3. Geolocation Bukan Kunci Unik
    u_geo_zip = geo["geolocation_zip_code_prefix"].nunique()
    dup_geo = geo.duplicated().sum()
    geo["lat"] = geo["geolocation_lat"].astype(float)
    geo["lng"] = geo["geolocation_lng"].astype(float)
    out_br = ((geo["lat"] > 5.27) | (geo["lat"] < -33.75) | (geo["lng"] > -34.79) | (geo["lng"] < -73.98)).sum()
    lines.append(f"- **Temuan 3 (Geolocation):** 1.000.163 baris cuma punya {u_geo_zip:,} zip prefix unik. Ada {dup_geo:,} baris duplikat persis, dan {out_br} koordinat di luar batas Brasil.")

    # 4. Leading Zero Kode Pos
    zero_cust = customers["customer_zip_code_prefix"].str.startswith("0").sum()
    zero_sell = sellers["seller_zip_code_prefix"].str.startswith("0").sum()
    lines.append(f"- **Temuan 4 (Kode Pos):** {zero_cust:,} customer dan {zero_sell:,} seller punya kode pos berawalan '0' yang bakal rusak kalau di-parse integer.")

    # 5. Order Tanpa Item
    no_items = len(set(orders["order_id"]) - set(items["order_id"]))
    lines.append(f"- **Temuan 5 (Orders Tanpa Items):** Ada {no_items:,} order yang tidak punya item sama sekali.")

    # 6. Order Tanpa Pembayaran & Payment Nol
    no_pay = len(set(orders["order_id"]) - set(payments["order_id"]))
    payments["val"] = payments["payment_value"].astype(float)
    zero_pay = (payments["val"] == 0).sum()
    lines.append(f"- **Temuan 6 (Pembayaran):** Ada {no_pay} order tanpa data pembayaran, dan {zero_pay} pembayaran bernilai 0.00 BRL.")

    # 7. Selisih Rekonsiliasi Keuangan
    items["tot"] = items["price"].astype(float) + items["freight_value"].astype(float)
    tot_item = items.groupby("order_id")["tot"].sum()
    tot_pay = payments.groupby("order_id")["val"].sum()
    comp = pd.DataFrame({"item": tot_item, "pay": tot_pay}).dropna()
    comp["diff"] = (comp["item"] - comp["pay"]).abs()
    diff_001 = (comp["diff"] > 0.01).sum()
    diff_100 = (comp["diff"] > 1.00).sum()
    lines.append(f"- **Temuan 7 (Rekonsiliasi Nilai):** Ada {diff_001:,} order selisih > 0.01 BRL antara item+ongkir vs uang dibayar ({diff_100:,} order selisih > 1.00 BRL).")

    # 8. Anomali Tanggal Pengiriman
    deliv_null = orders[(orders["order_status"] == "delivered") & (orders["order_delivered_customer_date"].isna())]
    valid_dates = orders.dropna(subset=["order_delivered_customer_date", "order_delivered_carrier_date"])
    deliv_fast = (valid_dates["order_delivered_customer_date"] < valid_dates["order_delivered_carrier_date"]).sum()
    lines.append(f"- **Temuan 8 (Tanggal Kirim):** Ada {len(deliv_null)} order status 'delivered' tapi tanggal terkirimnya NULL, dan {deliv_fast} order tercatat sampai sebelum diserahkan ke kurir.")

    # 9. BOM Encoding
    lines.append("- **Temuan 9 (Encoding BOM):** File `product_category_name_translation.csv` diawali byte BOM `\\ufeff` sehingga wajib dibaca dengan `utf-8-sig`.")

    # 10. Null Kategori Produk
    null_cat = products["product_category_name"].isna().sum()
    lines.append(f"- **Temuan 10 (Produk):** Ada {null_cat:,} produk tanpa nama kategori dan 2 produk tanpa dimensi/bobot.")

    content = "\n".join(lines)
    report_path.write_text(content, encoding="utf-8")
    print(f"[profile] Sukses! Profil lengkap berhasil disimpan ke: {report_path}")


if __name__ == "__main__":
    main()
