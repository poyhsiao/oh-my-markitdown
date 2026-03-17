# Requirements: Remove Queue from API

**Document ID:** REQ-2026-03-17-001
**Date:** 2026-03-17
**Author:** Kimhsiao
**Status:** Approved

---

## 1. Overview

### 1.1 Problem Statement

The current queue implementation in the API layer is problematic:

- Queue logic is embedded in each API endpoint
- `wait_for_slot()` blocks inside request handlers
- API is responsible for both "processing requests" and "queue management"
- The queue behavior is confusing from a user perspective

### 1.2 Goal

Remove queue functionality from API. When concurrency limit is reached, return HTTP 503 immediately. Let clients handle retry logic.

---

## 2. Functional Requirements

### FR-001: Remove Queue Waiting Behavior

**Priority:** High

**Description:** API must NOT queue requests. When busy, reject immediately.

**Acceptance Criteria:**
- [ ] No HTTP 202 responses for queue waiting
- [ ] No queue position tracking
- [ ] No `wait_for_slot()` blocking behavior

### FR-002: Return HTTP 503 When Busy

**Priority:** High

**Description:** When concurrency limit is reached, return HTTP 503 Service Unavailable.

**Acceptance Criteria:**
- [ ] HTTP 503 returned when `current_processing >= max_concurrent`
- [ ] Response includes error code `SERVICE_BUSY`
- [ ] Response includes user-friendly message

### FR-003: Simplified Concurrency Control

**Priority:** High

**Description:** Keep basic concurrency limiting via semaphore, but without queue.

**Acceptance Criteria:**
- [ ] `ConcurrencyManager.try_acquire()` returns boolean immediately
- [ ] `ConcurrencyManager.release()` properly releases slot
- [ ] No queue state maintained

### FR-004: Dependency Injection Pattern

**Priority:** Medium

**Description:** Use FastAPI dependency injection for slot acquisition.

**Acceptance Criteria:**
- [ ] `require_slot` dependency available
- [ ] Endpoint handlers are clean (no manual acquire/release in body)
- [ ] Slot released via `finally` block or dependency cleanup

### FR-005: Admin Queue Endpoint Removal

**Priority:** Low

**Description:** Remove `/api/v1/admin/queue` endpoint since queue no longer exists.

**Acceptance Criteria:**
- [ ] Endpoint removed from `api/system.py`
- [ ] 404 returned if accessed

---

## 3. Non-Functional Requirements

### NFR-001: Response Time

**Description:** Queue removal should not negatively impact response time.

**Acceptance Criteria:**
- [ ] Request handling time unchanged when slots available
- [ ] Immediate 503 response when busy (no delay)

### NFR-002: Code Maintainability

**Description:** Simplified code structure for easier maintenance.

**Acceptance Criteria:**
- [ ] Less than 100 lines in `concurrency.py` (currently 323 lines)
- [ ] No queue-related code in `response.py`
- [ ] Clear separation via dependency injection

### NFR-003: Backward Compatibility

**Description:** Clients using current API should handle the change gracefully.

**Acceptance Criteria:**
- [ ] Document breaking change (no more 202 responses)
- [ ] Update API version if needed
- [ ] Provide migration guide for clients

---

## 4. Constraints

### C-001: Must Not Break Existing Endpoints

All existing endpoints must continue to function correctly with the new concurrency model.

### C-002: Environment Variable Compatibility

`CONCURRENT_MAX_REQUESTS` must continue to work. `CONCURRENT_QUEUE_TIMEOUT` can be deprecated.

---

## 5. Out of Scope

- Implementing client-side retry logic
- External task queue system (Celery, RQ, etc.)
- Rate limiting (separate concern from concurrency)
- Authentication/authorization changes

---

## 6. Dependencies

- FastAPI framework
- Existing `ConcurrencyManager` (to be refactored)
- Existing error response format

---

## 7. Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| Clients expecting 202 responses | Medium | Document breaking change clearly |
| Increased 503 errors under load | Low | Expected behavior; clients should retry |
| Semaphore leak on exception | High | Use `finally` block consistently |

---

## 8. Success Metrics

- [ ] All tests pass
- [ ] No queue-related code in codebase
- [ ] HTTP 503 returned when busy
- [ ] Response time not degraded