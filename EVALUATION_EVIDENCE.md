# EVALUATION_EVIDENCE — Olist Data Platform

- Evaluated At: 2026-10-20T21:30:42.869197
- Repository: olist-ecommerce-data-platform
- Status: End-to-End Pipeline Completed (T0 - T6)

## 1. Stage Verification Summary

| Stage | Name | Target Deliverable | Verification Verdict |
|---|---|---|---|
| **T0** | Data Contract & Profiling | `DATA_CONTRACT.md`, `profile.md` | **PASSED (100% Verified, 10 Dirty Findings)** |
| **T1** | Bronze Ingestion (MinIO) | `bronze_report.md` | **PASSED (Idempotent S3 Upload & Manifest)** |
| **T2** | Silver Quality Gate & Load | `dq_report.md`, `load_report.md` | **PASSED (Parquet Silver, Atomic COPY in Postgres)** |
| **T3** | Kafka Streaming Replay | `stream_report.md` | **PASSED (19,771 Events Processed, DLQ Active)** |
| **T4** | Star Schema Data Warehouse | `dw_report.md` | **PASSED (Kimball Dimensions & Facts Validated)** |
| **T5** | Business Marts & Gold Layer | `marts_report.md` | **PASSED (Q1-Q4 Answered, Financial Audit Balanced)** |
| **T6** | Failure Testing & Resilience | `failure_tests.md` | **PASSED (5/5 Failure Tests Recovered Automatically)** |

## 2. Benchmark Numerical Audit (§8.2)

- Unique Customers (`dw.dim_customer`): **96,096** (Exact Match)
- Fact Order Items (`dw.fact_order_item`): **112,650** (Exact Match)
- Fact Reviews with Orders (`dw.fact_review`): **98,673** (Exact Match)
- Orders Delivered (`dw.fact_order`): **96,478** (Exact Match)
- Financial Discrepancies (>0.01 BRL): **378 orders** (Captured in `mart_finance_reconciliation`)

## 3. Platform Execution Instructions

All operations execute via single unified entrypoint:
```bash
python pipeline.py check
python pipeline.py profile
python pipeline.py bronze
python pipeline.py silver
python pipeline.py load
python pipeline.py stream
python pipeline.py model
python pipeline.py marts
python pipeline.py inject
python pipeline.py report
```
