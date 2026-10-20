# Data Marts & Financial Reconciliation Report

- Build Timestamp: 2026-10-20T21:06:38.568514
- Total Duration: 7.33 seconds
- Destination: PostgreSQL (`schema: mart`) + Parquet (`data/gold/`)

| Mart Name | Business Question Addressed | Row Count | Gold Parquet File |
|---|---|---|---|
| `mart.mart_revenue_monthly` | Q1: Monthly Revenue & Category Breakdown | 1,273 | `mart_revenue_monthly.parquet` |
| `mart.mart_delivery_by_state` | Q2: Delivery Delays & Review Impact | 27 | `mart_delivery_by_state.parquet` |
| `mart.mart_seller_performance` | Q3: Seller Compliance & SLA | 3,095 | `mart_seller_performance.parquet` |
| `mart.mart_customer_retention` | Q4: Customer Lifetime Value & Repeats | 93,350 | `mart_customer_retention.parquet` |
| `mart.mart_finance_reconciliation` | Financial Audit (Billed vs Paid) | 99,433 | `mart_finance_reconciliation.parquet` |

**Status: PASS (All business questions answered, Gold layer generated)**