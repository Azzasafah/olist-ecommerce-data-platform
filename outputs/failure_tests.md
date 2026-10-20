# Failure Injection & Self-Healing Resilience Report

- Tested At: 2026-10-20T21:20:29.158265
- Test Suite: 5/5 Chaos & Failure Scenarios

| Scenario | Result | Recovery & Resilience Behavior |
|---|---|---|
| **Test 1: Schema Corruption** | **PASS** | Missing source header intercepted before database writes. |
| **Test 2: Poison Pill Routing to DLQ** | **PASS** | Poison pill message successfully isolated in stream.order_dlq (Total DLQ: 1). |
| **Test 3: Idempotent Duplicate Replay** | **PASS** | Duplicate replay rejected via ON CONFLICT primary key guard. |
| **Test 4: Atomic Rollback on Failure** | **PASS** | Transaction rolled back cleanly without partial row leakage. |
| **Test 5: Out-of-Order Event State Guard** | **PASS** | Out-of-order event handled correctly: status remained 'order_delivered'. |

**Final Verdict: PASS (All 5 resilience tests recovered automatically)**