"""
Concurrency control module with queue management.

Implements request queuing when max concurrent requests is reached.
"""

import asyncio
import time
from typing import Dict, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
import uuid

import os


@dataclass
class ConcurrencySettings:
    """Concurrency settings from environment."""
    max_requests: int = 3
    queue_timeout: int = 600  # 10 minutes
    
    @classmethod
    def from_env(cls) -> "ConcurrencySettings":
        """Load settings from environment variables."""
        return cls(
            max_requests=int(os.getenv("CONCURRENT_MAX_REQUESTS", "3")),
            queue_timeout=int(os.getenv("CONCURRENT_QUEUE_TIMEOUT", "600")),
        )


@dataclass
class QueueItem:
    """Represents a queued request."""
    request_id: str
    request_type: str  # convert, youtube, audio, video, url
    status: str  # queued, processing, completed, failed
    position: int
    enqueued_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    
    def wait_time(self) -> float:
        """Calculate wait time in queue."""
        if self.started_at:
            return self.started_at - self.enqueued_at
        return time.time() - self.enqueued_at


class ConcurrencyManager:
    """
    Manages concurrent request limits with queue waiting.
    
    Features:
    - Maximum concurrent requests limit
    - Queue with position tracking
    - Timeout for queue waiting
    - Request tracking
    """
    
    def __init__(
        self,
        max_concurrent: int = 3,
        queue_timeout: int = 600  # 10 minutes
    ):
        self.max_concurrent = max_concurrent
        self.queue_timeout = queue_timeout
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._queue: Dict[str, QueueItem] = {}
        self._processing: Dict[str, QueueItem] = {}
        self._lock = asyncio.Lock()
        self._counter = 0
    
    @property
    def current_processing(self) -> int:
        """Get current number of processing requests."""
        return len(self._processing)
    
    @property
    def queue_length(self) -> int:
        """Get current queue length."""
        return len(self._queue)
    
    @property
    def is_available(self) -> bool:
        """Check if a slot is available."""
        return self.current_processing < self.max_concurrent
    
    async def enqueue(
        self,
        request_type: str,
        request_id: Optional[str] = None
    ) -> QueueItem:
        """
        Add a request to the queue.
        
        Args:
            request_type: Type of request (convert, youtube, etc.)
            request_id: Optional request ID
            
        Returns:
            QueueItem with position info
        """
        if request_id is None:
            request_id = f"req-{uuid.uuid4().hex[:12]}"
        
        async with self._lock:
            self._counter += 1
            position = len(self._queue) + 1
            
            item = QueueItem(
                request_id=request_id,
                request_type=request_type,
                status="queued",
                position=position
            )
            
            self._queue[request_id] = item
            return item
    
    async def start_processing(self, request_id: str) -> bool:
        """
        Move a request from queue to processing.
        
        Args:
            request_id: Request ID to start processing
            
        Returns:
            True if successfully started
        """
        async with self._lock:
            if request_id not in self._queue:
                return False
            
            item = self._queue.pop(request_id)
            item.status = "processing"
            item.started_at = time.time()
            
            # Update positions for remaining items
            for i, rid in enumerate(self._queue.keys(), 1):
                self._queue[rid].position = i
            
            self._processing[request_id] = item
            return True
    
    async def complete(self, request_id: str, success: bool = True) -> Optional[QueueItem]:
        """
        Mark a request as completed.
        
        Args:
            request_id: Request ID to complete
            success: Whether processing succeeded
            
        Returns:
            The completed QueueItem
        """
        async with self._lock:
            if request_id not in self._processing:
                return None
            
            item = self._processing.pop(request_id)
            item.status = "completed" if success else "failed"
            item.completed_at = time.time()
            
            return item
    
    async def acquire(
        self,
        request_type: str,
        request_id: Optional[str] = None
    ) -> tuple[bool, Optional[QueueItem]]:
        """
        Acquire a processing slot.
        
        If queue is full, returns queue position info.
        If slot acquired, returns (True, None).
        
        Args:
            request_type: Type of request
            request_id: Optional request ID
            
        Returns:
            Tuple of (acquired, queue_item)
            - If acquired: (True, None)
            - If queued: (False, QueueItem with position)
        """
        # Check if slot available immediately
        if self.is_available:
            if request_id is None:
                request_id = f"req-{uuid.uuid4().hex[:12]}"
            
            async with self._lock:
                item = QueueItem(
                    request_id=request_id,
                    request_type=request_type,
                    status="processing",
                    position=0,
                    started_at=time.time()
                )
                self._processing[request_id] = item
            
            await self._semaphore.acquire()
            return True, None
        
        # Need to queue
        item = await self.enqueue(request_type, request_id)
        return False, item
    
    async def wait_for_slot(
        self,
        request_type: str,
        request_id: Optional[str] = None,
        timeout: Optional[int] = None
    ) -> tuple[bool, Optional[QueueItem]]:
        """
        Wait for a processing slot with timeout.
        
        Args:
            request_type: Type of request
            request_id: Optional request ID
            timeout: Timeout in seconds (defaults to queue_timeout)
            
        Returns:
            Tuple of (acquired, queue_item)
        """
        if timeout is None:
            timeout = self.queue_timeout
        
        acquired, item = await self.acquire(request_type, request_id)
        if acquired:
            return True, None
        
        if item is None:
            return False, None
        
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            async with self._lock:
                if item.request_id in self._queue:
                    items = list(self._queue.values())
                    for i, queued_item in enumerate(items, 1):
                        queued_item.position = i
                    
                    if item.position == 1 and self.is_available:
                        self._queue.pop(item.request_id)
                        item.status = "processing"
                        item.started_at = time.time()
                        self._processing[item.request_id] = item
                        return True, None
            
            await asyncio.sleep(0.5)
        
        async with self._lock:
            if item.request_id in self._queue:
                self._queue.pop(item.request_id)
        
        return False, item
    
    def release(self, request_id: str) -> None:
        """Release a processing slot."""
        if request_id in self._processing:
            self._processing.pop(request_id)
            try:
                self._semaphore.release()
            except ValueError:
                pass  # Semaphore already at max
    
    def get_queue_status(self) -> Dict[str, Any]:
        """
        Get current queue status.
        
        Returns:
            Dict with queue info
        """
        queue_list = []
        
        # Add processing items
        for item in self._processing.values():
            queue_list.append({
                "request_id": item.request_id,
                "type": item.request_type,
                "status": item.status
            })
        
        # Add queued items
        for item in sorted(self._queue.values(), key=lambda x: x.position):
            queue_list.append({
                "request_id": item.request_id,
                "type": item.request_type,
                "status": item.status,
                "position": item.position
            })
        
        return {
            "current_processing": self.current_processing,
            "max_concurrent": self.max_concurrent,
            "queue_length": self.queue_length,
            "queue": queue_list
        }


# Global concurrency manager instance
_concurrency_manager: Optional[ConcurrencyManager] = None


def get_concurrency_manager() -> ConcurrencyManager:
    global _concurrency_manager
    
    if _concurrency_manager is None:
        settings = ConcurrencySettings.from_env()
        _concurrency_manager = ConcurrencyManager(
            max_concurrent=settings.max_requests,
            queue_timeout=settings.queue_timeout
        )
    
    return _concurrency_manager


def reset_concurrency_manager() -> None:
    """Reset the global concurrency manager (for testing)."""
    global _concurrency_manager
    _concurrency_manager = None