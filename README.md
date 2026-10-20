# Olist E-Commerce End-to-End Data Platform

Production-grade data engineering platform built on Brazilian E-Commerce public dataset (Olist: 99,441 orders, 1.5M rows across 9 raw tables). Demonstrates end-to-end Medallion Lakehouse architecture, real-time event streaming with Apache Kafka, Kimball Star Schema data warehousing, and automated resilience testing.

---

## 🏛️ Platform Architecture

```
Raw CSVs (Kaggle) 
   │
   ▼
MinIO Object Storage (Bronze Layer: Idempotent & Versioned Manifest)
   │
   ▼
Data Quality Gate & Quarantine (Pandas / PyArrow)
   │
   ├──► Quarantined Anomalies (data/quarantine/*.csv)
   │
   ▼
MinIO Parquet & PostgreSQL Raw Schema (Silver Layer: Bulk COPY)
   │
   ├──► Apache Kafka (Real-Time Event Replay & State Machine)
   │       └──► stream.order_events & stream.order_current_status & DLQ
   │
   ▼
PostgreSQL Data Warehouse (Gold DW: Kimball Star Schema with PK/FK Integrity)
   │       ├── dim_customer (96,096 unique people)
   │       ├── dim_seller, dim_product, dim_date
   │       └── fact_order, fact_order_item, fact_review
   │
   ▼
Business Data Marts & Financial Audit (mart.* + Gold Parquet)
   ├── Q1: Monthly Revenue & Category Breakdown
   ├── Q2: Delivery Delays & Review Score Impact
   ├── Q3: Seller SLA Compliance
   ├── Q4: Customer Lifetime Value & Retention
   └── Reconciliation: Billed Items vs Real Payments
```

---

## ⚡ Tech Stack

- **Storage & Lakehouse:** MinIO (S3-compatible Object Storage), Apache Parquet, PyArrow
- **Database & Warehouse:** PostgreSQL 16 (Raw, Stream, DW, Mart schemas), psycopg v3
- **Streaming & Replay:** Apache Kafka & Kafka UI (Event-driven lifecycle state machine)
- **Programming & Orchestration:** Python 3.10+, Docker Compose, Pandas

---

## 🚀 Key Engineering Highlights

1. **Strict Data Contract & 10 Dirty Findings:**
   - Differentiated `customer_id` (transaction-level, 99,441) from `customer_unique_id` (real person, 96,096) to model true customer grain.
   - Enforced 5-digit text zip codes (`zfill(5)`), preventing leading-zero loss in São Paulo regions (23,995 customer records saved).
   - Handled UTF-8 BOM (`\ufeff`) in translation files and deduplicated review records.
2. **Idempotent Bronze Lakehouse:**
   - MinIO ingestion computes MD5 checksums against `manifest.json`. Zero redundant re-uploads on identical data.
3. **High-Speed Atomic PostgreSQL Ingestion:**
   - Utilized `COPY ... FROM STDIN` streaming to load 738,000+ geolocation rows in ~3.4 seconds within atomic transactions.
4. **Resilient Streaming Engine:**
   - Replayed 19,771 chronological order events (`created` → `approved` → `shipped` → `delivered`).
   - Idempotent state machine rejects out-of-order state regression and routes poison pills to Dead Letter Queue (`stream.order_dlq`).
5. **Self-Healing Resilience Testing:**
   - Passed 5 automated chaos scenarios including schema corruption, poison pill isolation, duplicate injection, and transaction rollback.

---

## 💻 Quickstart & Execution

All stages run through a unified single entrypoint CLI:

```bash
# 1. Initialize environment & start Docker infrastructure
python pipeline.py init
python pipeline.py up

# 2. Run end-to-end pipeline
python pipeline.py check      # Verify raw datasets
python pipeline.py profile    # Automated profiling -> outputs/profile.md
python pipeline.py bronze     # Ingest raw CSV to MinIO Bronze Lakehouse
python pipeline.py silver     # Quality gate & Parquet transformation
python pipeline.py load       # Atomic bulk load to PostgreSQL raw schema
python pipeline.py stream     # Kafka event streaming & state machine
python pipeline.py model      # Build Star Schema (dw.*) in PostgreSQL
python pipeline.py marts      # Build business marts & export Gold Parquet
python pipeline.py inject     # Run 5 automated failure resilience tests
python pipeline.py report     # Compile EVALUATION_EVIDENCE.md & RUNBOOK.md
```

---

## 📊 Verification & Numerical Audit

| Benchmark Metric | Target (§8.2) | Achieved Result | Verdict |
|---|---|---|---|
| Unique Customers (`dim_customer`) | 96,096 | **96,096** | Exact Match |
| Total Item Records (`fact_order_item`) | 112,650 | **112,650** | Exact Match |
| Reviewed Orders (`fact_review`) | 98,673 | **98,673** | Exact Match |
| Delivered Orders (`fact_order`) | 96,478 | **96,478** | Exact Match |
| Stream Events Processed | 19,771 | **19,771** | Zero Data Loss |
| Failure Tests Recovered | 5 / 5 | **5 / 5** | 100% Passed |

---

## 📁 Repository Structure

```
├── DATA_CONTRACT.md            # Data contract & 10 dirty findings documentation
├── EVALUATION_EVIDENCE.md      # Consolidated benchmark verification evidence
├── RUNBOOK.md                  # Infrastructure operations & disaster recovery runbook
├── docker-compose.yml          # Big data stack (Postgres, Kafka, MinIO, Kafka UI)
├── pipeline.py                 # Single unified entrypoint CLI
├── scripts/
│   ├── check_dataset.py        # Raw CSV integrity verifier
│   ├── profile_dataset.py      # Automated statistical profiling engine
│   ├── ingest_bronze.py        # Idempotent MinIO lakehouse ingestion
│   ├── process_silver.py       # Data quality gate & Parquet converter
│   ├── load_raw_postgres.py    # Atomic PostgreSQL COPY loader
│   ├── stream_pipeline.py      # Kafka producer replay & idempotent consumer
│   ├── build_data_warehouse.py # Kimball Star Schema modeler
│   ├── build_data_marts.py     # Analytical data marts & finance reconciliation
│   ├── run_failure_tests.py    # Chaos testing & self-healing verification
│   └── generate_final_report.py# Final evidence compiler
└── outputs/                    # Auto-generated verification reports & markdown evidence
```
