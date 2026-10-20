# Data Warehouse (Star Schema) Report

- Build Timestamp: 2026-10-20T20:49:34.193807
- Total Duration: 1.47 seconds
- Architecture: Kimball Star Schema (`schema: dw`)

| Table Name | Role | Row Count | Primary Key |
|---|---|---|---|
| `dw.dim_customer` | Dimension | 96,096 | `customer_unique_id` |
| `dw.dim_seller` | Dimension | 3,095 | `seller_id` |
| `dw.dim_product` | Dimension | 32,951 | `product_id` |
| `dw.dim_date` | Dimension | 1,461 | `date_id` |
| `dw.fact_order` | Fact | 99,433 | `order_id` |
| `dw.fact_order_item` | Fact | 112,650 | `(order_id, order_item_id)` |
| `dw.fact_review` | Fact | 98,673 | `order_id` |

**Status: PASS (PK constraints verified, Star Schema modeled)**