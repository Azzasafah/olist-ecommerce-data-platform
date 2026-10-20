# Automated Data Profiling Report — Olist Dataset

## 1. Ringkasan Tabel & Kualitas Kolom

### `orders` (99,441 baris, 8 kolom)

| Kolom | Null Count | Null % | Nilai Unik | Contoh Nilai |
|---|---|---|---|---|
| order_id | 0 | 0.00% | 99,441 | `e481f51cbdc54678b7cc49136...` |
| customer_id | 0 | 0.00% | 99,441 | `9ef432eb6251297304e76186b...` |
| order_status | 0 | 0.00% | 8 | `delivered` |
| order_purchase_timestamp | 0 | 0.00% | 98,875 | `2017-10-02 10:56:33` |
| order_approved_at | 160 | 0.16% | 90,733 | `2017-10-02 11:07:15` |
| order_delivered_carrier_date | 1,783 | 1.79% | 81,018 | `2017-10-04 19:55:00` |
| order_delivered_customer_date | 2,965 | 2.98% | 95,664 | `2017-10-10 21:25:13` |
| order_estimated_delivery_date | 0 | 0.00% | 459 | `2017-10-18 00:00:00` |

### `order_items` (112,650 baris, 7 kolom)

| Kolom | Null Count | Null % | Nilai Unik | Contoh Nilai |
|---|---|---|---|---|
| order_id | 0 | 0.00% | 98,666 | `00010242fe8c5a6d1ba2dd792...` |
| order_item_id | 0 | 0.00% | 21 | `1` |
| product_id | 0 | 0.00% | 32,951 | `4244733e06e7ecb4970a6e268...` |
| seller_id | 0 | 0.00% | 3,095 | `48436dade18ac8b2bce089ec2...` |
| shipping_limit_date | 0 | 0.00% | 93,318 | `2017-09-19 09:45:35` |
| price | 0 | 0.00% | 5,968 | `58.90` |
| freight_value | 0 | 0.00% | 6,999 | `13.29` |

### `order_payments` (103,886 baris, 5 kolom)

| Kolom | Null Count | Null % | Nilai Unik | Contoh Nilai |
|---|---|---|---|---|
| order_id | 0 | 0.00% | 99,440 | `b81ef226f3fe1789b1e8b2aca...` |
| payment_sequential | 0 | 0.00% | 29 | `1` |
| payment_type | 0 | 0.00% | 5 | `credit_card` |
| payment_installments | 0 | 0.00% | 24 | `8` |
| payment_value | 0 | 0.00% | 29,077 | `99.33` |

### `customers` (99,441 baris, 5 kolom)

| Kolom | Null Count | Null % | Nilai Unik | Contoh Nilai |
|---|---|---|---|---|
| customer_id | 0 | 0.00% | 99,441 | `06b8999e2fba1a1fbc88172c0...` |
| customer_unique_id | 0 | 0.00% | 96,096 | `861eff4711a542e4b93843c6d...` |
| customer_zip_code_prefix | 0 | 0.00% | 14,994 | `14409` |
| customer_city | 0 | 0.00% | 4,119 | `franca` |
| customer_state | 0 | 0.00% | 27 | `SP` |

### `order_reviews` (99,224 baris, 7 kolom)

| Kolom | Null Count | Null % | Nilai Unik | Contoh Nilai |
|---|---|---|---|---|
| review_id | 0 | 0.00% | 98,410 | `7bc2406110b926393aa56f80a...` |
| order_id | 0 | 0.00% | 98,673 | `73fc7af87114b39712e6da79b...` |
| review_score | 0 | 0.00% | 5 | `4` |
| review_comment_title | 87,656 | 88.34% | 4,527 | `recomendo` |
| review_comment_message | 58,247 | 58.70% | 36,159 | `Recebi bem antes do prazo...` |
| review_creation_date | 0 | 0.00% | 636 | `2018-01-18 00:00:00` |
| review_answer_timestamp | 0 | 0.00% | 98,248 | `2018-01-18 21:46:59` |

### `products` (32,951 baris, 9 kolom)

| Kolom | Null Count | Null % | Nilai Unik | Contoh Nilai |
|---|---|---|---|---|
| product_id | 0 | 0.00% | 32,951 | `1e9e8ef04dbcff4541ed26657...` |
| product_category_name | 610 | 1.85% | 73 | `perfumaria` |
| product_name_lenght | 610 | 1.85% | 66 | `40` |
| product_description_lenght | 610 | 1.85% | 2,960 | `287` |
| product_photos_qty | 610 | 1.85% | 19 | `1` |
| product_weight_g | 2 | 0.01% | 2,204 | `225` |
| product_length_cm | 2 | 0.01% | 99 | `16` |
| product_height_cm | 2 | 0.01% | 102 | `10` |
| product_width_cm | 2 | 0.01% | 95 | `14` |

### `sellers` (3,095 baris, 4 kolom)

| Kolom | Null Count | Null % | Nilai Unik | Contoh Nilai |
|---|---|---|---|---|
| seller_id | 0 | 0.00% | 3,095 | `3442f8959a84dea7ee197c632...` |
| seller_zip_code_prefix | 0 | 0.00% | 2,246 | `13023` |
| seller_city | 0 | 0.00% | 611 | `campinas` |
| seller_state | 0 | 0.00% | 23 | `SP` |

### `geolocation` (1,000,163 baris, 5 kolom)

| Kolom | Null Count | Null % | Nilai Unik | Contoh Nilai |
|---|---|---|---|---|
| geolocation_zip_code_prefix | 0 | 0.00% | 19,015 | `01037` |
| geolocation_lat | 0 | 0.00% | 717,372 | `-23.54562128115268` |
| geolocation_lng | 0 | 0.00% | 717,615 | `-46.63929204800168` |
| geolocation_city | 0 | 0.00% | 8,011 | `sao paulo` |
| geolocation_state | 0 | 0.00% | 27 | `SP` |

### `category_translation` (71 baris, 2 kolom)

| Kolom | Null Count | Null % | Nilai Unik | Contoh Nilai |
|---|---|---|---|---|
| product_category_name | 0 | 0.00% | 71 | `beleza_saude` |
| product_category_name_english | 0 | 0.00% | 71 | `health_beauty` |

## 2. Investigasi Temuan 'Kotor' Riil

- **Temuan 1 (Customers):** `customer_id` unik = 99,441, tapi `customer_unique_id` (orang asli) cuma 96,096. Ada 2,997 pelanggan yang belanja ulang.
- **Temuan 2 (Reviews):** `review_id` tidak unik (98,410 unik dari 99,224 baris). Ada 547 order yang punya > 1 review.
- **Temuan 3 (Geolocation):** 1.000.163 baris cuma punya 19,015 zip prefix unik. Ada 261,831 baris duplikat persis, dan 42 koordinat di luar batas Brasil.
- **Temuan 4 (Kode Pos):** 23,995 customer dan 1,027 seller punya kode pos berawalan '0' yang bakal rusak kalau di-parse integer.
- **Temuan 5 (Orders Tanpa Items):** Ada 775 order yang tidak punya item sama sekali.
- **Temuan 6 (Pembayaran):** Ada 1 order tanpa data pembayaran, dan 9 pembayaran bernilai 0.00 BRL.
- **Temuan 7 (Rekonsiliasi Nilai):** Ada 378 order selisih > 0.01 BRL antara item+ongkir vs uang dibayar (249 order selisih > 1.00 BRL).
- **Temuan 8 (Tanggal Kirim):** Ada 8 order status 'delivered' tapi tanggal terkirimnya NULL, dan 23 order tercatat sampai sebelum diserahkan ke kurir.
- **Temuan 9 (Encoding BOM):** File `product_category_name_translation.csv` diawali byte BOM `\ufeff` sehingga wajib dibaca dengan `utf-8-sig`.
- **Temuan 10 (Produk):** Ada 610 produk tanpa nama kategori dan 2 produk tanpa dimensi/bobot.