# RUNBOOK — Olist Data Platform Operations

## 1. System Requirements & Setup
- Docker Desktop with Docker Compose v2+
- Python 3.10+
- Dependencies: `pip install -r requirements.txt`

## 2. Infrastructure Operations
```bash
# Start all platform containers
python pipeline.py up

# Check status of services
docker compose ps

# Shutdown platform
python pipeline.py down
```

## 3. Disaster Recovery & Troubleshooting
- **PostgreSQL Socket Down:** Verify Docker Desktop daemon is running and execute `python pipeline.py up`.
- **Kafka Port Conflict:** Adjust `KAFKA_UI_PORT` or `KAFKA_HOST_PORT` in `.env`.
- **Corrupted Ingestion Stream:** Inspect poison pills isolated in `SELECT * FROM stream.order_dlq;`.
