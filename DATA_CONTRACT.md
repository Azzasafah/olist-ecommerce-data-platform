# DATA_CONTRACT — Olist Data Platform

Sumber: Brazilian E-Commerce Public Dataset by Olist (Kaggle), 99.441 order, 9 file CSV.
Semua stempel waktu: waktu lokal Brasil tanpa zona. Mata uang: BRL. Kode pos: **teks 5 digit** di semua tabel.

## 1. Skema Tabel Target

### orders (`olist_orders_dataset.csv`)
- `order_id`: text (PK, 99.441 unik)
- `customer_id`: text (FK ke customers)
- `order_status`: text (delivered, shipped, canceled, dll)
- `order_purchase_timestamp`: timestamp
- `order_approved_at`: timestamp (nullable)
- `order_delivered_carrier_date`: timestamp (nullable)
- `order_delivered_customer_date`: timestamp (nullable)
- `order_estimated_delivery_date`: timestamp

### order_items (`olist_order_items_dataset.csv`)
- `order_id`: text (FK)
- `order_item_id`: integer (PK gabungan: order_id + order_item_id)
- `product_id`: text (FK ke products)
- `seller_id`: text (FK ke sellers)
- `shipping_limit_date`: timestamp
- `price`: numeric(10, 2)
- `freight_value`: numeric(10, 2)

### order_payments (`olist_order_payments_dataset.csv`)
- `order_id`: text (FK)
- `payment_sequential`: integer (PK gabungan: order_id + payment_sequential)
- `payment_type`: text (credit_card, boleto, voucher, debit_card, not_defined)
- `payment_installments`: integer
- `payment_value`: numeric(10, 2)

### order_reviews (`olist_order_reviews_dataset.csv`)
- `review_id`: text (bukan PK murni, ada duplikat)
- `order_id`: text (FK ke orders, 547 order punya > 1 review)
- `review_score`: integer (skor 1-5)
- `review_comment_title`: text (nullable)
- `review_comment_message`: text (nullable)
- `review_creation_date`: timestamp
- `review_answer_timestamp`: timestamp

### customers (`olist_customers_dataset.csv`)
- `customer_id`: text (PK transaksi, 99.441 unik)
- `customer_unique_id`: text (ID orang sesungguhnya, 96.096 unik)
- `customer_zip_code_prefix`: text(5) (wajib teks 5 digit)
- `customer_city`: text
- `customer_state`: text(2)

### sellers (`olist_sellers_dataset.csv`)
- `seller_id`: text (PK, 3.095 unik)
- `seller_zip_code_prefix`: text(5) (wajib teks 5 digit)
- `seller_city`: text
- `seller_state`: text(2)

### products (`olist_products_dataset.csv`)
- `product_id`: text (PK, 32.951 unik)
- `product_category_name`: text (nullable, 610 kosong)
- `product_name_lenght`: integer (nullable)
- `product_description_lenght`: integer (nullable)
- `product_photos_qty`: integer (nullable)
- `product_weight_g`: numeric (nullable, 2 kosong)
- `product_length_cm`: numeric (nullable)
- `product_height_cm`: numeric (nullable)
- `product_width_cm`: numeric (nullable)

### geolocation (`olist_geolocation_dataset.csv`)
- `geolocation_zip_code_prefix`: text(5) (bukan PK unik, 1 prefix = banyak koordinat)
- `geolocation_lat`: numeric
- `geolocation_lng`: numeric
- `geolocation_city`: text
- `geolocation_state`: text(2)

### category_translation (`product_category_name_translation.csv`)
- `product_category_name`: text (PK, diawali BOM \ufeff)
- `product_category_name_english`: text

---

## 2. Temuan "Kotor" dan Keputusannya

| # | Tabel | Temuan | Angka | Keputusan | Diterapkan di |
|---|---|---|---|---|---|
| 1 | customers | Dua jenis ID pelanggan | 99.441 `customer_id` vs 96.096 `customer_unique_id` (2.997 repeat buyers) | Grain `dim_customer` memakai `customer_unique_id` | T4 (`dim_customer`) |
| 2 | reviews | Review ID tidak unik & order multi-review | 98.410 review_id unik; 547 order punya > 1 review | Ambil review terbaru berdasarkan `review_answer_timestamp` | T2 / T4 (`fact_review`) |
| 3 | geolocation | Zip prefix bukan 1:1 & koordinat anomali | 19.015 zip prefix dari 1M baris; 261.831 duplikat; 42 koordinat di luar Brasil | Karantina koordinat di luar Brasil; agregasikan median lat/lng per prefix | T2 & T4 (`dim_location`) |
| 4 | customers & sellers | Hilang angka 0 di depan kode pos | 23.995 customer & 1.027 seller kode pos berawalan '0' | Tipe kode pos wajib string 5 digit (`zfill(5)`) | T1 & T2 |
| 5 | orders vs items | Order tanpa produk | 775 order tidak punya baris di items | Catat sebagai order batal/kosong; gunakan LEFT JOIN di fact | T2 & T4 (`fact_order`) |
| 6 | orders vs payments | Order tanpa pembayaran & pembayaran 0 | 1 order tanpa pembayaran; 9 transaksi senilai 0.00 BRL | Karantina nilai 0 / tangani sebagai voucher diskon 100% | T2 (Silver gate) |
| 7 | items vs payments | Selisih nilai barang vs uang dibayar | 378 order selisih > 0.01 BRL (249 selisih > 1.00 BRL) | Sediakan tabel rekonsiliasi finance khusus | T5 (`mart_finance_reconciliation`) |
| 8 | orders | Inkonsistensi tanggal pengiriman | 8 order delivered tanggal NULL; 23 order sampai sebelum kurir terima | Tandai kualitas data; hitung durasi pengiriman hanya jika tanggal valid | T2 (Silver gate) |
| 9 | category_translation | File diawali byte BOM `\ufeff` | 1 file translation | Gunakan encoding `utf-8-sig` saat ingest & reading | T1 & T2 |
| 10 | products | Kategori dan dimensi NULL | 610 produk kategori NULL; 2 produk dimensi NULL | Imputasi kategori NULL dengan string `'unknown'` | T2 & T4 (`dim_product`) |

---

## 3. Keputusan Pemodelan Lanjutan
- **Grain `dim_customer`**: 1 baris per `customer_unique_id` (orang asli), bukan per transaksi order.
- **Kebijakan `fact_review`**: Jika 1 order memiliki multiple review, deduplikasi dengan memilih baris dengan `review_answer_timestamp` paling akhir.
- **Metrik `is_late`**: Bernilai TRUE jika `order_delivered_customer_date > order_estimated_delivery_date`.
- **Bulan Lengkap**: Periode analitik pendapatan bulanan difokuskan pada Januari 2017 s/d Agustus 2018 (karena September 2016 dan Oktober 2018 datanya tidak lengkap).
