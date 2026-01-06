"""
Batch vs Real-time processing mode.

Implements V5-015: Auto-detect context and use appropriate mode.
- New emails → Real-time processing
- Archive scanning → Batch processing with progress tracking
"""

import asyncio
import logging
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class ProcessingMode(Enum):
    """Processing mode for email classification."""
    REALTIME = "realtime"  # Immediate processing, one at a time
    BATCH = "batch"        # Batch processing with progress tracking


@dataclass
class BatchJob:
    """A batch processing job."""
    job_id: str
    email_ids: List[str]
    status: str = "pending"
    progress: int = 0
    total: int = 0
    started_at: float = 0.0
    completed_at: float = 0.0
    results: Dict = field(default_factory=dict)
    error: Optional[str] = None
    
    def __post_init__(self):
        self.total = len(self.email_ids)
        if not self.results:
            self.results = {"success": [], "failed": [], "skipped": []}


class BatchProcessor:
    """
    Batch processing manager for email classification.
    
    Features:
    - Auto-detect processing mode from context
    - Batch job management with progress tracking
    - Rate limiting between batches
    - Cancellation support
    
    Usage:
        processor = BatchProcessor(config)
        
        # Auto-detect mode
        mode = processor.detect_mode({"count": 100, "source": "archive"})
        
        if mode == ProcessingMode.BATCH:
            job_id = processor.create_job(email_ids)
            processor.start_job(job_id, classify_fn)
            status = processor.get_status(job_id)
    """
    
    def __init__(self, config: Optional[Dict] = None):
        """
        Initialize batch processor.
        
        Args:
            config: Configuration with:
                - batch_size: Emails per batch (default: 50)
                - batch_delay: Seconds between batches (default: 0.5)
                - max_concurrent: Max concurrent jobs (default: 1)
                - realtime_threshold: Max emails for real-time (default: 5)
        """
        config = config or {}
        
        self.batch_size = config.get("batch_size", 50)
        self.batch_delay = config.get("batch_delay", 0.5)
        self.max_concurrent = config.get("max_concurrent", 1)
        self.realtime_threshold = config.get("realtime_threshold", 5)
        
        # Job storage
        self._jobs: Dict[str, BatchJob] = {}
        self._active_jobs: int = 0
        self._lock = threading.Lock()
        
        # Cancellation flags
        self._cancel_flags: Dict[str, bool] = {}
    
    def detect_mode(self, context: Dict) -> ProcessingMode:
        """
        Auto-detect appropriate processing mode.
        
        Args:
            context: Processing context with:
                - source: "new_mail", "archive", "bulk_import"
                - count: Number of emails to process
                - email_age_hours: Age of oldest email
        
        Returns:
            ProcessingMode.REALTIME or ProcessingMode.BATCH
        """
        # Explicit source indicators
        source = context.get("source", "")
        if source in ("archive", "bulk_import", "manual_batch"):
            return ProcessingMode.BATCH
        
        if source == "new_mail":
            return ProcessingMode.REALTIME
        
        # Count-based detection
        count = context.get("count", 1)
        if count > self.realtime_threshold:
            return ProcessingMode.BATCH
        
        # Age-based detection (old emails likely archive)
        age_hours = context.get("email_age_hours", 0)
        if age_hours > 24 and count > 1:
            return ProcessingMode.BATCH
        
        return ProcessingMode.REALTIME
    
    def create_job(self, email_ids: List[str]) -> str:
        """
        Create a new batch job.
        
        Args:
            email_ids: List of email IDs to process
        
        Returns:
            Job ID string
        """
        job_id = str(uuid.uuid4())[:8]
        
        job = BatchJob(
            job_id=job_id,
            email_ids=email_ids
        )
        
        with self._lock:
            self._jobs[job_id] = job
            self._cancel_flags[job_id] = False
        
        logger.info(f"Created batch job {job_id} with {len(email_ids)} emails")
        return job_id
    
    def get_status(self, job_id: str) -> Optional[Dict]:
        """
        Get status of a batch job.
        
        Args:
            job_id: Job identifier
        
        Returns:
            Status dict or None if job not found
        """
        with self._lock:
            job = self._jobs.get(job_id)
        
        if not job:
            return None
        
        elapsed = 0.0
        if job.started_at:
            end_time = job.completed_at or time.time()
            elapsed = end_time - job.started_at
        
        return {
            "job_id": job_id,
            "status": job.status,
            "progress": job.progress,
            "total": job.total,
            "elapsed_seconds": round(elapsed, 1),
            "success_count": len(job.results.get("success", [])),
            "failed_count": len(job.results.get("failed", [])),
            "skipped_count": len(job.results.get("skipped", [])),
            "error": job.error
        }
    
    def get_results(self, job_id: str) -> Optional[Dict]:
        """
        Get detailed results of a completed job.
        
        Args:
            job_id: Job identifier
        
        Returns:
            Results dict or None if job not found
        """
        with self._lock:
            job = self._jobs.get(job_id)
        
        if not job:
            return None
        
        return {
            "job_id": job_id,
            "status": job.status,
            "results": job.results,
            "started_at": job.started_at,
            "completed_at": job.completed_at
        }
    
    def cancel_job(self, job_id: str) -> bool:
        """
        Cancel a running job.
        
        Args:
            job_id: Job identifier
        
        Returns:
            True if cancellation was requested
        """
        with self._lock:
            if job_id in self._cancel_flags:
                self._cancel_flags[job_id] = True
                logger.info(f"Cancellation requested for job {job_id}")
                return True
        return False
    
    def start_job(
        self,
        job_id: str,
        classify_fn: Callable[[str], Optional[Dict]],
        progress_callback: Optional[Callable[[str, int, int], None]] = None
    ) -> bool:
        """
        Start processing a batch job.
        
        This runs synchronously. For async processing, use start_job_async.
        
        Args:
            job_id: Job identifier
            classify_fn: Function that takes email_id and returns classification result
            progress_callback: Optional callback(job_id, current, total)
        
        Returns:
            True if job completed successfully
        """
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return False
            
            if self._active_jobs >= self.max_concurrent:
                job.status = "queued"
                return False
            
            self._active_jobs += 1
            job.status = "running"
            job.started_at = time.time()
        
        try:
            self._process_job(job, classify_fn, progress_callback)
            return job.status == "completed"
        finally:
            with self._lock:
                self._active_jobs -= 1
    
    def _process_job(
        self,
        job: BatchJob,
        classify_fn: Callable[[str], Optional[Dict]],
        progress_callback: Optional[Callable[[str, int, int], None]] = None
    ) -> None:
        """Internal job processing loop."""
        
        for i, email_id in enumerate(job.email_ids):
            # Check for cancellation
            with self._lock:
                if self._cancel_flags.get(job.job_id, False):
                    job.status = "cancelled"
                    job.completed_at = time.time()
                    logger.info(f"Job {job.job_id} cancelled at {i}/{job.total}")
                    return
            
            try:
                result = classify_fn(email_id)
                
                if result:
                    job.results["success"].append({
                        "email_id": email_id,
                        "result": result
                    })
                else:
                    job.results["skipped"].append(email_id)
                    
            except Exception as e:
                job.results["failed"].append({
                    "email_id": email_id,
                    "error": str(e)
                })
                logger.warning(f"Failed to process email {email_id}: {e}")
            
            # Update progress
            job.progress = int((i + 1) / job.total * 100)
            
            # Call progress callback
            if progress_callback:
                try:
                    progress_callback(job.job_id, i + 1, job.total)
                except Exception:
                    pass
            
            # Rate limiting between batches
            if (i + 1) % self.batch_size == 0 and i + 1 < job.total:
                time.sleep(self.batch_delay)
        
        job.status = "completed"
        job.completed_at = time.time()
        
        elapsed = job.completed_at - job.started_at
        logger.info(
            f"Job {job.job_id} completed: "
            f"{len(job.results['success'])} success, "
            f"{len(job.results['failed'])} failed, "
            f"{len(job.results['skipped'])} skipped "
            f"in {elapsed:.1f}s"
        )
    
    async def start_job_async(
        self,
        job_id: str,
        classify_fn: Callable[[str], Optional[Dict]],
        progress_callback: Optional[Callable[[str, int, int], None]] = None
    ) -> bool:
        """
        Start processing a batch job asynchronously.
        
        Args:
            job_id: Job identifier
            classify_fn: Function that takes email_id and returns result
            progress_callback: Optional callback(job_id, current, total)
        
        Returns:
            True if job completed successfully
        """
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return False
            
            if self._active_jobs >= self.max_concurrent:
                job.status = "queued"
                return False
            
            self._active_jobs += 1
            job.status = "running"
            job.started_at = time.time()
        
        try:
            await self._process_job_async(job, classify_fn, progress_callback)
            return job.status == "completed"
        finally:
            with self._lock:
                self._active_jobs -= 1
    
    async def _process_job_async(
        self,
        job: BatchJob,
        classify_fn: Callable[[str], Optional[Dict]],
        progress_callback: Optional[Callable[[str, int, int], None]] = None
    ) -> None:
        """Internal async job processing loop."""
        
        for i, email_id in enumerate(job.email_ids):
            # Check for cancellation
            with self._lock:
                if self._cancel_flags.get(job.job_id, False):
                    job.status = "cancelled"
                    job.completed_at = time.time()
                    return
            
            try:
                # Run sync function in thread pool
                result = await asyncio.to_thread(classify_fn, email_id)
                
                if result:
                    job.results["success"].append({
                        "email_id": email_id,
                        "result": result
                    })
                else:
                    job.results["skipped"].append(email_id)
                    
            except Exception as e:
                job.results["failed"].append({
                    "email_id": email_id,
                    "error": str(e)
                })
            
            # Update progress
            job.progress = int((i + 1) / job.total * 100)
            
            if progress_callback:
                try:
                    progress_callback(job.job_id, i + 1, job.total)
                except Exception:
                    pass
            
            # Rate limiting
            if (i + 1) % self.batch_size == 0 and i + 1 < job.total:
                await asyncio.sleep(self.batch_delay)
        
        job.status = "completed"
        job.completed_at = time.time()
    
    def cleanup_old_jobs(self, max_age_hours: int = 24) -> int:
        """
        Remove completed jobs older than max_age.
        
        Args:
            max_age_hours: Maximum job age in hours
        
        Returns:
            Number of jobs removed
        """
        cutoff = time.time() - (max_age_hours * 3600)
        removed = 0
        
        with self._lock:
            to_remove = []
            for job_id, job in self._jobs.items():
                if job.status in ("completed", "cancelled", "failed"):
                    if job.completed_at and job.completed_at < cutoff:
                        to_remove.append(job_id)
            
            for job_id in to_remove:
                del self._jobs[job_id]
                self._cancel_flags.pop(job_id, None)
                removed += 1
        
        if removed:
            logger.debug(f"Cleaned up {removed} old batch jobs")
        
        return removed
    
    def list_jobs(self) -> List[Dict]:
        """List all jobs with basic status."""
        with self._lock:
            return [self.get_status(job_id) for job_id in self._jobs]


# Global batch processor instance
_batch_processor: Optional[BatchProcessor] = None
_processor_lock = threading.Lock()


def get_batch_processor(config: Optional[Dict] = None) -> BatchProcessor:
    """
    Get or create the global batch processor.
    
    Args:
        config: Optional configuration dict
    
    Returns:
        Global BatchProcessor instance
    """
    global _batch_processor
    
    with _processor_lock:
        if _batch_processor is None:
            _batch_processor = BatchProcessor(config)
        return _batch_processor
