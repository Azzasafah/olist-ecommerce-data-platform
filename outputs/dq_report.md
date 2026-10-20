# Silver Layer Quality & Transformation Report

- Generated At: 2026-10-20T18:06:50.033033
- Format: Apache Parquet (Clean) + CSV (Quarantined)

| Table | Raw Rows | Quarantined Rows | Clean Silver Rows | Status |
|---|---|---|---|---|
| `customers` | 99,441 | 0 | 99,441 | **PASS** |
| `sellers` | 3,095 | 0 | 3,095 | **PASS** |
| `geolocation` | 1,000,163 | 261,864 | 738,299 | **PASS + QUARANTINE** |
| `orders` | 99,441 | 8 | 99,433 | **PASS + QUARANTINE** |
| `order_items` | 112,650 | 0 | 112,650 | **PASS** |
| `order_payments` | 103,886 | 9 | 103,877 | **PASS + QUARANTINE** |
| `order_reviews` | 99,224 | 0 | 99,224 | **PASS** |
| `products` | 32,951 | 0 | 32,951 | **PASS** |
| `product_category_name_translation` | 71 | 0 | 71 | **PASS** |