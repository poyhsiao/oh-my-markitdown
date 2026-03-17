# Remove Queue from API - Design Document

**Date:** 2026-03-17
**Author:** Kimhsiao
**Status:** Approved

---

## Problem Statement

The current queue implementation in the API layer has several issues:

1. Queue logic is embedded in each API endpoint
2. `wait_for_slot()` blocks inside request handlers
3. API is responsible for both "processing requests" and "queue management"
4. No true asynchronous task processing mechanism

**User Feedback:** "Queue functionality shouldn't be in the API"

---

## Solution: Remove Queue, Return 503 on Busy

When concurrency limit is reached, return HTTP 503 (Service Unavailable) immediately. Let clients handle retry logic.

---

## Architecture Changes

### Before

```
API Endpoint
    ↓
wait_for_slot() → blocks or returns queue position (HTTP 202)
    ↓
Process request
```

### After

```
API Endpoint
    ↓
Depends(require_slot) → HTTP 503 if busy, or acquire slot
    ↓
Process request
    ↓
release_slot() in finally block
```

---

## Implementation Details

### 1. Simplified ConcurrencyManager

**File:** `api/concurrency.py`

Remove all queue-related code, keep only counting functionality:

```python
class ConcurrencyManager:
    def __init__(self, max_concurrent: int = 3):
        self.max_concurrent = max_concurrent
        self._semaphore = asyncio.Semaphore(max_concurrent)
    
    def try_acquire(self) -> bool:
        """Try to acquire a slot. Returns False if full."""
        return self._semaphore.acquire_nowait()
    
    def release(self) -> None:
        """Release a processing slot."""
        try:
            self._semaphore.release()
        except ValueError:
            pass
```

**Removed:**
- `QueueItem` dataclass
- `enqueue()` method
- `wait_for_slot()` method
- `acquire()` method
- `get_queue_status()` method
- All queue state tracking

### 2. New Dependency Injection

**File:** `api/dependencies.py` (new)

```python
def require_slot():
    """
    FastAPI dependency that acquires a concurrency slot.
    Raises HTTPException(503) when limit reached.
    """
    manager = get_concurrency_manager()
    
    if not manager.try_acquire():
        raise HTTPException(
            status_code=503,
            detail=error_response(
                code=ErrorCodes.SERVICE_BUSY,
                message="Service is busy. Please retry later.",
            )
        )
    
    return manager.release
```

### 3. Endpoint Modification

**Pattern:**

```python
@api_router.post("/convert/file")
async def convert_file_endpoint(
    release_slot = Depends(require_slot),  # Inject slot
    file: UploadFile = File(...),
    ...
):
    try:
        # Process request
        return result
    finally:
        release_slot()  # Always release
```

**Endpoints to modify:**

| Endpoint | Action |
|----------|--------|
| `/convert/file` | Replace queue logic with `Depends(require_slot)` |
| `/convert/youtube` | Replace queue logic with `Depends(require_slot)` |
| `/convert/audio` | Add `Depends(require_slot)` |
| `/convert/video` | Add `Depends(require_slot)` |
| `/convert/url` | Add `Depends(require_slot)` |

### 4. Code Removal

| File | Action |
|------|--------|
| `api/concurrency.py` | Rewrite, remove queue code |
| `api/response.py` | Remove `queue_waiting_response()` |
| `api/response.py` | Remove `ErrorCodes.QUEUE_WAITING` |
| `api/system.py` | Remove `/admin/queue` endpoint |

### 5. Environment Variables

| Variable | Action |
|----------|--------|
| `CONCURRENT_QUEUE_TIMEOUT` | Remove (no longer needed) |
| `CONCURRENT_MAX_REQUESTS` | Keep |

---

## Error Response Format

**HTTP 503 Response:**

```json
{
    "success": false,
    "error": {
        "code": "SERVICE_BUSY",
        "message": "Service is busy. Please retry later."
    },
    "request_id": "req-xxx",
    "timestamp": "2026-03-17T..."
}
```

---

## Migration Notes

1. Clients must implement retry logic on 503
2. No more HTTP 202 queue-waiting responses
3. Simpler mental model: either process or reject

---

## Testing Checklist

- [ ] Verify 503 returned when limit reached
- [ ] Verify slots released after request completes
- [ ] Verify slots released on exception
- [ ] Verify concurrent requests work correctly
- [ ] Verify no memory leaks in semaphore