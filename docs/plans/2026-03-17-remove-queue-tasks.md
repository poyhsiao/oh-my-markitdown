# Tasks: Remove Queue from API

**Document ID:** TASK-2026-03-17-001
**Date:** 2026-03-17
**Author:** Kimhsiao
**Status:** Ready for Implementation
**Related Requirements:** REQ-2026-03-17-001
**Related Design:** 2026-03-17-remove-queue-design.md

---

## Task Summary

| ID | Task | Priority | Est. Effort | Status |
|----|------|----------|-------------|--------|
| T-001 | Refactor `concurrency.py` | High | 30 min | [ ] Pending |
| T-002 | Create `dependencies.py` | High | 15 min | [ ] Pending |
| T-003 | Update `response.py` | Medium | 10 min | [ ] Pending |
| T-004 | Update `/convert/file` endpoint | High | 20 min | [ ] Pending |
| T-005 | Update `/convert/youtube` endpoint | High | 15 min | [ ] Pending |
| T-006 | Update `/convert/audio` endpoint | Medium | 10 min | [ ] Pending |
| T-007 | Update `/convert/video` endpoint | Medium | 10 min | [ ] Pending |
| T-008 | Update `/convert/url` endpoint | Medium | 15 min | [ ] Pending |
| T-009 | Remove `/admin/queue` endpoint | Low | 5 min | [ ] Pending |
| T-010 | Update tests | High | 30 min | [ ] Pending |
| T-011 | Update documentation | Medium | 15 min | [ ] Pending |

**Total Estimated Effort:** ~3 hours

---

## Detailed Tasks

### T-001: Refactor `concurrency.py`

**Priority:** High
**Est. Effort:** 30 min
**Dependencies:** None

**Description:**
Rewrite `api/concurrency.py` to remove all queue functionality.

**Subtasks:**
- [ ] Remove `QueueItem` dataclass
- [ ] Remove `enqueue()` method
- [ ] Remove `wait_for_slot()` method
- [ ] Remove `acquire()` method
- [ ] Remove `get_queue_status()` method
- [ ] Remove `_queue` and `_counter` instance variables
- [ ] Keep only `_semaphore` for counting
- [ ] Implement `try_acquire() -> bool`
- [ ] Keep existing `release()` method
- [ ] Remove `ConcurrencySettings.queue_timeout`
- [ ] Update `reset_concurrency_manager()` if needed

**Acceptance Criteria:**
- [ ] File is under 100 lines
- [ ] No queue-related code remains
- [ ] `try_acquire()` returns `True` if slot available, `False` otherwise
- [ ] No imports related to queue tracking (time, uuid for queue items)

**Files to Modify:**
- `api/concurrency.py`

---

### T-002: Create `dependencies.py`

**Priority:** High
**Est. Effort:** 15 min
**Dependencies:** T-001

**Description:**
Create new file for FastAPI dependency injection.

**Subtasks:**
- [ ] Create `api/dependencies.py`
- [ ] Implement `require_slot()` dependency function
- [ ] Import `get_concurrency_manager` from concurrency module
- [ ] Import `error_response`, `ErrorCodes` from response module
- [ ] Return `release` function for cleanup

**Acceptance Criteria:**
- [ ] `require_slot` is a valid FastAPI dependency
- [ ] Returns release function when slot acquired
- [ ] Raises HTTPException(503) when limit reached

**Files to Create:**
- `api/dependencies.py`

---

### T-003: Update `response.py`

**Priority:** Medium
**Est. Effort:** 10 min
**Dependencies:** None

**Description:**
Remove queue-related response helpers and error codes.

**Subtasks:**
- [ ] Remove `queue_waiting_response()` function
- [ ] Remove `ErrorCodes.QUEUE_WAITING` constant
- [ ] Add `ErrorCodes.SERVICE_BUSY` constant
- [ ] Verify no other queue references

**Acceptance Criteria:**
- [ ] No `queue_waiting_response` function
- [ ] No `QUEUE_WAITING` error code
- [ ] `SERVICE_BUSY` error code exists

**Files to Modify:**
- `api/response.py`

---

### T-004: Update `/convert/file` Endpoint

**Priority:** High
**Est. Effort:** 20 min
**Dependencies:** T-001, T-002

**Description:**
Replace queue logic with dependency injection in `/api/v1/convert/file`.

**Subtasks:**
- [ ] Add `release_slot = Depends(require_slot)` parameter
- [ ] Remove `wait_for_slot()` call and related code block
- [ ] Remove queue waiting response logic
- [ ] Add `release_slot()` in `finally` block
- [ ] Remove `manager.release(request_id)` from existing finally
- [ ] Verify error handling still works

**Acceptance Criteria:**
- [ ] No `wait_for_slot()` call
- [ ] No queue-related code in handler body
- [ ] Slot released on success and error
- [ ] HTTP 503 returned when busy

**Files to Modify:**
- `api/main.py` (lines ~342-483)

---

### T-005: Update `/convert/youtube` Endpoint

**Priority:** High
**Est. Effort:** 15 min
**Dependencies:** T-001, T-002

**Description:**
Replace queue logic with dependency injection in `/api/v1/convert/youtube`.

**Subtasks:**
- [ ] Add `release_slot = Depends(require_slot)` parameter
- [ ] Remove `wait_for_slot()` call and related code block
- [ ] Remove queue waiting response logic
- [ ] Add `release_slot()` in `finally` block
- [ ] Remove existing `manager.release(request_id)`

**Acceptance Criteria:**
- [ ] No queue-related code in handler
- [ ] Slot properly released

**Files to Modify:**
- `api/main.py` (lines ~507-603)

---

### T-006: Update `/convert/audio` Endpoint

**Priority:** Medium
**Est. Effort:** 10 min
**Dependencies:** T-001, T-002

**Description:**
Add dependency injection to `/api/v1/convert/audio`.

**Subtasks:**
- [ ] Add `release_slot = Depends(require_slot)` parameter
- [ ] Add `try/finally` block for slot release
- [ ] Ensure cleanup happens on error

**Acceptance Criteria:**
- [ ] Concurrency limit enforced
- [ ] Slot released on completion

**Files to Modify:**
- `api/main.py` (lines ~606-673)

---

### T-007: Update `/convert/video` Endpoint

**Priority:** Medium
**Est. Effort:** 10 min
**Dependencies:** T-001, T-002

**Description:**
Add dependency injection to `/api/v1/convert/video`.

**Subtasks:**
- [ ] Add `release_slot = Depends(require_slot)` parameter
- [ ] Add `try/finally` block for slot release
- [ ] Ensure cleanup happens on error

**Acceptance Criteria:**
- [ ] Concurrency limit enforced
- [ ] Slot released on completion

**Files to Modify:**
- `api/main.py` (lines ~676-750)

---

### T-008: Update `/convert/url` Endpoint

**Priority:** Medium
**Est. Effort:** 15 min
**Dependencies:** T-001, T-002

**Description:**
Add dependency injection to `/api/v1/convert/url`.

**Subtasks:**
- [ ] Add `release_slot = Depends(require_slot)` parameter
- [ ] Add `try/finally` block for slot release
- [ ] Ensure cleanup happens on error

**Acceptance Criteria:**
- [ ] Concurrency limit enforced
- [ ] Slot released on completion

**Files to Modify:**
- `api/main.py` (lines ~946-1295)

---

### T-009: Remove `/admin/queue` Endpoint

**Priority:** Low
**Est. Effort:** 5 min
**Dependencies:** T-001

**Description:**
Remove the queue status endpoint since queue no longer exists.

**Subtasks:**
- [ ] Remove `get_queue_status()` endpoint function
- [ ] Remove related import if no longer used

**Acceptance Criteria:**
- [ ] No `/api/v1/admin/queue` endpoint
- [ ] No `get_queue_status` function

**Files to Modify:**
- `api/system.py` (lines ~431-450)

---

### T-010: Update Tests

**Priority:** High
**Est. Effort:** 30 min
**Dependencies:** T-001 through T-009

**Description:**
Update or create tests for the new concurrency behavior.

**Subtasks:**
- [ ] Update existing concurrency tests (if any)
- [ ] Add test for HTTP 503 when limit reached
- [ ] Add test for successful request when slot available
- [ ] Add test for slot release on success
- [ ] Add test for slot release on exception
- [ ] Remove queue-related tests

**Acceptance Criteria:**
- [ ] All tests pass
- [ ] No queue-related test cases
- [ ] 503 behavior tested

**Files to Modify:**
- `tests/api/test_concurrency.py` (if exists)
- `tests/api/test_system.py`
- Create new test file if needed

---

### T-011: Update Documentation

**Priority:** Medium
**Est. Effort:** 15 min
**Dependencies:** T-001 through T-010

**Description:**
Update API documentation to reflect changes.

**Subtasks:**
- [ ] Update `CHANGELOG.md` with breaking change note
- [ ] Update `docs/API_REFERENCE.md` (if exists)
- [ ] Remove queue-related documentation
- [ ] Add note about HTTP 503 behavior
- [ ] Update any client examples if needed

**Acceptance Criteria:**
- [ ] Breaking change documented
- [ ] No queue references in docs
- [ ] 503 behavior explained

**Files to Modify:**
- `CHANGELOG.md`
- `docs/API_REFERENCE.md` (if exists)
- `README.md` (if needed)

---

## Execution Order

```
T-001 ──┬── T-002 ──┬── T-004
        │           ├── T-005
        │           ├── T-006
        │           ├── T-007
        │           └── T-008
        │
        ├── T-003 ──┘
        │
        └── T-009
              │
              └── T-010 ── T-011
```

**Parallelizable:**
- T-001 and T-003 can run in parallel
- T-004 through T-008 can run in parallel after T-001 and T-002 complete

---

## Verification Checklist

After all tasks complete:

- [ ] `api/concurrency.py` under 100 lines
- [ ] No queue-related code in codebase
- [ ] `grep -r "queue" api/` returns no results (except comments/docs)
- [ ] `grep -r "wait_for_slot" api/` returns no results
- [ ] `grep -r "QUEUE_WAITING" api/` returns no results
- [ ] All tests pass
- [ ] HTTP 503 returned when concurrent limit reached
- [ ] Normal requests work correctly