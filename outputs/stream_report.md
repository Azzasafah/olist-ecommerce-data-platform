# Kafka Streaming & Real-Time Ingestion Report

- Generated At: 2026-10-20T19:48:39.901177
- Kafka Topic: `olist.orders.events`
- Total Events Produced: 19,771
- Events Processed by Consumer: 19,771
- Duplicate Events Filtered: 0

## Destination Stream Tables in PostgreSQL:

- `stream.order_events`: Append-only audit log of raw events.
- `stream.order_current_status`: Current lifecycle state per order (Idempotent State Machine).
- `stream.order_dlq`: Dead Letter Queue for corrupted messages.

**Status: PASS (Zero data loss, Idempotency verified)**