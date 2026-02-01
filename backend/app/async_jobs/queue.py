"""
Async processing module.
Background jobs, webhooks, and queue management.
"""

import asyncio
import json
import uuid
from typing import Dict, Any, Optional, List, Callable, Coroutine
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass, asdict
import hashlib


class JobStatus(Enum):
    """Status of background jobs"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRYING = "retrying"


class JobPriority(Enum):
    """Job priority levels"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class BackgroundJob:
    """Background job definition"""
    job_id: str
    job_type: str
    status: JobStatus
    priority: JobPriority
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    payload: Dict[str, Any] = None
    result: Optional[Any] = None
    error: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3
    webhook_url: Optional[str] = None
    
    @classmethod
    def create(
        cls,
        job_type: str,
        payload: Dict[str, Any],
        priority: JobPriority = JobPriority.NORMAL,
        max_retries: int = 3,
        webhook_url: Optional[str] = None
    ) -> "BackgroundJob":
        return cls(
            job_id=str(uuid.uuid4()),
            job_type=job_type,
            status=JobStatus.PENDING,
            priority=priority,
            created_at=datetime.utcnow(),
            payload=payload,
            max_retries=max_retries,
            webhook_url=webhook_url
        )
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "job_id": self.job_id,
            "job_type": self.job_type,
            "status": self.status.value,
            "priority": self.priority.value,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "payload": self.payload,
            "result": self.result,
            "error": self.error,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "webhook_url": self.webhook_url
        }


class JobQueue:
    """
    In-memory job queue with priority support.
    For production, this would use Redis/RabbitMQ.
    """
    
    def __init__(self):
        self._queue: asyncio.PriorityQueue = asyncio.PriorityQueue()
        self._jobs: Dict[str, BackgroundJob] = {}
        self._running: Dict[str, BackgroundJob] = {}
        self._completed: Dict[str, BackgroundJob] = {}
        self._handlers: Dict[str, Callable] = {}
        self._max_completed = 1000
    
    def register_handler(self, job_type: str, handler: Callable):
        """Register a handler for a job type"""
        self._handlers[job_type] = handler
    
    async def enqueue(self, job: BackgroundJob) -> str:
        """Add job to queue"""
        # Use negative priority so higher numbers = higher priority
        await self._queue.put((-job.priority.value, job.created_at, job.job_id))
        self._jobs[job.job_id] = job
        return job.job_id
    
    async def dequeue(self) -> Optional[BackgroundJob]:
        """Get next job from queue"""
        try:
            _, _, job_id = await self._queue.get()
            job = self._jobs.pop(job_id, None)
            if job:
                self._running[job_id] = job
            return job
        except asyncio.QueueEmpty:
            return None
    
    def complete_job(self, job_id: str, result: Any, error: Optional[str] = None):
        """Mark job as complete"""
        job = self._running.pop(job_id, None)
        if job:
            job.completed_at = datetime.utcnow()
            job.result = result
            job.error = error
            job.status = JobStatus.FAILED if error else JobStatus.COMPLETED
            
            self._completed[job_id] = job
            
            # Trim completed jobs
            if len(self._completed) > self._max_completed:
                oldest = next(iter(self._completed))
                del self._completed[oldest]
    
    def get_job(self, job_id: str) -> Optional[BackgroundJob]:
        """Get job by ID"""
        # Check all storages
        for storage in [self._jobs, self._running, self._completed]:
            if job_id in storage:
                return storage[job_id]
        return None
    
    def get_queue_status(self) -> Dict[str, Any]:
        """Get current queue status"""
        return {
            "pending": len(self._jobs),
            "running": len(self._running),
            "completed": len(self._completed),
            "handlers": list(self._handlers.keys())
        }


class BackgroundWorker:
    """
    Background job worker.
    Processes jobs from the queue.
    """
    
    def __init__(
        self,
        queue: JobQueue,
        max_concurrent: int = 5,
        poll_interval: float = 1.0
    ):
        self.queue = queue
        self.max_concurrent = max_concurrent
        self.poll_interval = poll_interval
        self._running = False
        self._workers: List[asyncio.Task] = []
        self._webhook_client = None
    
    async def start(self):
        """Start the worker"""
        self._running = True
        
        # Start worker tasks
        for i in range(self.max_concurrent):
            task = asyncio.create_task(self._worker_loop())
            self._workers.append(task)
        
        print(f"Started {self.max_concurrent} background workers")
    
    async def stop(self):
        """Stop the worker gracefully"""
        self._running = False
        
        # Cancel all workers
        for task in self._workers:
            task.cancel()
        
        # Wait for completion
        await asyncio.gather(*self._workers, return_exceptions=True)
        print("Background workers stopped")
    
    async def _worker_loop(self):
        """Main worker loop"""
        while self._running:
            try:
                job = await self.queue.dequeue()
                
                if job:
                    await self._process_job(job)
                else:
                    # No jobs, wait before checking again
                    await asyncio.sleep(self.poll_interval)
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Worker error: {e}")
                await asyncio.sleep(self.poll_interval)
    
    async def _process_job(self, job: BackgroundJob):
        """Process a single job"""
        handler = self.queue._handlers.get(job.job_type)
        
        if not handler:
            self.queue.complete_job(
                job.job_id,
                None,
                f"No handler registered for job type: {job.job_type}"
            )
            return
        
        job.status = JobStatus.RUNNING
        job.started_at = datetime.utcnow()
        
        try:
            result = await handler(job.payload)
            self.queue.complete_job(job.job_id, result)
            
            # Send webhook notification
            if job.webhook_url:
                await self._send_webhook(job, success=True)
                
        except Exception as e:
            error_msg = str(e)
            
            # Check if should retry
            if job.retry_count < job.max_retries:
                job.retry_count += 1
                job.status = JobStatus.RETRYING
                job.error = error_msg
                
                # Re-queue with delay
                await asyncio.sleep(2 ** job.retry_count)  # Exponential backoff
                await self.queue.enqueue(job)
            else:
                self.queue.complete_job(job.job_id, None, error_msg)
                
                # Send webhook notification
                if job.webhook_url:
                    await self._send_webhook(job, success=False, error=error_msg)
    
    async def _send_webhook(
        self,
        job: BackgroundJob,
        success: bool,
        error: Optional[str] = None
    ):
        """Send webhook notification"""
        if not job.webhook_url:
            return
        
        try:
            import httpx
            
            payload = {
                "job_id": job.job_id,
                "job_type": job.job_type,
                "status": "completed" if success else "failed",
                "completed_at": datetime.utcnow().isoformat(),
                "result": job.result if success else None,
                "error": error
            }
            
            async with httpx.AsyncClient() as client:
                await client.post(
                    job.webhook_url,
                    json=payload,
                    timeout=30.0
                )
        except Exception as e:
            print(f"Webhook delivery failed: {e}")


class QueryJobHandler:
    """
    Handler for long-running query jobs.
    """
    
    def __init__(self, query_executor, cache_client):
        self.query_executor = query_executor
        self.cache = cache_client
    
    async def __call__(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Execute query in background"""
        query = payload.get("query")
        connection_id = payload.get("connection_id")
        user_id = payload.get("user_id")
        
        # Execute query
        result = await self.query_executor.execute(query, connection_id)
        
        # Cache result
        cache_key = f"query_result:{hashlib.sha256(query.encode()).hexdigest()[:16]}"
        await self.cache.set(cache_key, result, ttl=3600)
        
        return {
            "query": query[:200],
            "row_count": result.get("row_count", 0),
            "cache_key": cache_key
        }


class ExportJobHandler:
    """
    Handler for export jobs.
    """
    
    def __init__(self, export_manager, storage_client):
        self.export_manager = export_manager
        self.storage = storage_client
    
    async def __call__(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Execute export in background"""
        query = payload.get("query")
        format = payload.get("format", "csv")
        
        # Get data from query
        # This would call the query executor
        data = payload.get("data", [])
        
        # Generate export
        export_result = await self.export_manager.export(
            data,
            format,
            filename_base=payload.get("filename", "export")
        )
        
        # Store file
        file_key = f"exports/{uuid.uuid4()}/{export_result['filename']}"
        await self.storage.store(file_key, export_result["content"])
        
        return {
            "file_key": file_key,
            "filename": export_result["filename"],
            "format": format,
            "row_count": export_result["row_count"],
            "size_bytes": export_result["size_bytes"]
        }


class WebhookManager:
    """
    Manage webhook subscriptions and deliveries.
    """
    
    def __init__(self):
        self._subscriptions: Dict[str, Dict[str, Any]] = {}
        self._delivery_log: List[Dict] = []
    
    def subscribe(
        self,
        event_type: str,
        url: str,
        secret: Optional[str] = None,
        filters: Optional[Dict] = None
    ) -> str:
        """Subscribe to webhook events"""
        subscription_id = str(uuid.uuid4())
        
        self._subscriptions[subscription_id] = {
            "id": subscription_id,
            "event_type": event_type,
            "url": url,
            "secret": secret,
            "filters": filters or {},
            "created_at": datetime.utcnow().isoformat(),
            "active": True
        }
        
        return subscription_id
    
    def unsubscribe(self, subscription_id: str) -> bool:
        """Remove webhook subscription"""
        if subscription_id in self._subscriptions:
            del self._subscriptions[subscription_id]
            return True
        return False
    
    async def trigger_event(
        self,
        event_type: str,
        payload: Dict[str, Any]
    ):
        """Trigger event and notify subscribers"""
        import httpx
        import hmac
        import hashlib
        
        # Find matching subscriptions
        matching = [
            sub for sub in self._subscriptions.values()
            if sub["event_type"] == event_type and sub["active"]
        ]
        
        for subscription in matching:
            try:
                # Add signature if secret exists
                headers = {"Content-Type": "application/json"}
                
                if subscription.get("secret"):
                    signature = hmac.new(
                        subscription["secret"].encode(),
                        json.dumps(payload).encode(),
                        hashlib.sha256
                    ).hexdigest()
                    headers["X-Webhook-Signature"] = f"sha256={signature}"
                
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        subscription["url"],
                        json=payload,
                        headers=headers,
                        timeout=30.0
                    )
                
                # Log delivery
                self._delivery_log.append({
                    "subscription_id": subscription["id"],
                    "event_type": event_type,
                    "timestamp": datetime.utcnow().isoformat(),
                    "status_code": response.status_code,
                    "success": response.status_code < 400
                })
                
            except Exception as e:
                self._delivery_log.append({
                    "subscription_id": subscription["id"],
                    "event_type": event_type,
                    "timestamp": datetime.utcnow().isoformat(),
                    "error": str(e),
                    "success": False
                })


# Global instances
_job_queue: Optional[JobQueue] = None
_background_worker: Optional[BackgroundWorker] = None
_webhook_manager: Optional[WebhookManager] = None


def get_job_queue() -> JobQueue:
    """Get global job queue"""
    global _job_queue
    if _job_queue is None:
        _job_queue = JobQueue()
    return _job_queue


def get_webhook_manager() -> WebhookManager:
    """Get global webhook manager"""
    global _webhook_manager
    if _webhook_manager is None:
        _webhook_manager = WebhookManager()
    return _webhook_manager


async def start_background_worker(max_concurrent: int = 5):
    """Start the background worker"""
    global _background_worker
    if _background_worker is None:
        _background_worker = BackgroundWorker(
            get_job_queue(),
            max_concurrent=max_concurrent
        )
        await _background_worker.start()
    return _background_worker


async def stop_background_worker():
    """Stop the background worker"""
    global _background_worker
    if _background_worker:
        await _background_worker.stop()
        _background_worker = None


async def enqueue_query_job(
    query: str,
    connection_id: str,
    user_id: Optional[str] = None,
    webhook_url: Optional[str] = None
) -> str:
    """Enqueue a long-running query job"""
    queue = get_job_queue()
    
    job = BackgroundJob.create(
        job_type="query",
        payload={
            "query": query,
            "connection_id": connection_id,
            "user_id": user_id
        },
        priority=JobPriority.NORMAL,
        webhook_url=webhook_url
    )
    
    return await queue.enqueue(job)


async def enqueue_export_job(
    data: List[Dict],
    format: str,
    filename: str,
    webhook_url: Optional[str] = None
) -> str:
    """Enqueue an export job"""
    queue = get_job_queue()
    
    job = BackgroundJob.create(
        job_type="export",
        payload={
            "data": data,
            "format": format,
            "filename": filename
        },
        priority=JobPriority.LOW,
        webhook_url=webhook_url
    )
    
    return await queue.enqueue(job)
