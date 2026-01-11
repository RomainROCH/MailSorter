"""
Unit tests for batch processor (V5-015).
"""

import time
from unittest.mock import Mock

from backend.core.batch_processor import (
    BatchProcessor,
    BatchJob,
    ProcessingMode,
    JobStatus,
    get_processor,
    reset_processor,
)


class TestBatchProcessor:
    """Tests for BatchProcessor."""

    def setup_method(self):
        """Create processor for testing."""
        self.processor = BatchProcessor(
            {
                "batch_size": 10,
                "batch_delay_ms": 100,
                "realtime_timeout_ms": 5000,
                "max_concurrent_jobs": 3,
            }
        )

    def test_detect_mode_single_email(self):
        """Should detect realtime mode for single email."""
        mode = self.processor.detect_mode(email_count=1)
        assert mode == ProcessingMode.REALTIME

    def test_detect_mode_bulk(self):
        """Should detect batch mode for bulk operations."""
        mode = self.processor.detect_mode(email_count=100)
        assert mode == ProcessingMode.BATCH

    def test_detect_mode_force_batch(self):
        """Should respect forced batch mode."""
        mode = self.processor.detect_mode(
            email_count=1, force_mode=ProcessingMode.BATCH
        )
        assert mode == ProcessingMode.BATCH

    def test_create_batch_job(self):
        """Should create batch job."""
        emails = [{"id": i, "subject": f"Email {i}"} for i in range(5)]

        job = self.processor.create_job(emails)

        assert job.id is not None
        assert job.status == JobStatus.PENDING
        assert job.total == 5
        assert job.processed == 0

    def test_job_progress(self):
        """Should track job progress."""
        job = BatchJob(
            id="test-job",
            emails=[{} for _ in range(10)],
            status=JobStatus.RUNNING,
            total=10,
            processed=3,
        )

        assert job.progress == 0.3

    def test_job_complete(self):
        """Should detect completed job."""
        job = BatchJob(
            id="test-job", emails=[], status=JobStatus.COMPLETED, total=10, processed=10
        )

        assert job.is_complete is True

    def test_list_jobs(self):
        """Should list all jobs."""
        # Create some jobs
        self.processor.create_job([{"id": 1}])
        self.processor.create_job([{"id": 2}])

        jobs = self.processor.list_jobs()

        assert len(jobs) == 2

    def test_get_job(self):
        """Should get job by ID."""
        job = self.processor.create_job([{"id": 1}])

        retrieved = self.processor.get_job(job.id)

        assert retrieved is not None
        assert retrieved.id == job.id

    def test_get_nonexistent_job(self):
        """Should return None for nonexistent job."""
        job = self.processor.get_job("nonexistent-id")
        assert job is None

    def test_cancel_job(self):
        """Should cancel pending job."""
        job = self.processor.create_job([{"id": i} for i in range(10)])

        success = self.processor.cancel_job(job.id)

        assert success is True
        assert self.processor.get_job(job.id).status == JobStatus.CANCELLED

    def test_cancel_completed_job_fails(self):
        """Should not cancel completed job."""
        job = self.processor.create_job([{"id": 1}])
        job.status = JobStatus.COMPLETED

        success = self.processor.cancel_job(job.id)

        assert success is False

    def test_batch_iterator(self):
        """Should iterate in batches."""
        emails = [{"id": i} for i in range(25)]

        batches = list(self.processor.batch_iterator(emails))

        assert len(batches) == 3  # 10 + 10 + 5
        assert len(batches[0]) == 10
        assert len(batches[2]) == 5

    def test_realtime_process(self):
        """Should process in realtime mode."""
        classify_fn = Mock(return_value={"folder": "Inbox", "confidence": 0.9})

        email = {"id": 1, "subject": "Test"}
        result = self.processor.process_realtime(email, classify_fn)

        classify_fn.assert_called_once_with(email)
        assert result["folder"] == "Inbox"

    def test_get_stats(self):
        """Should return processor statistics."""
        self.processor.create_job([{"id": 1}])

        stats = self.processor.get_stats()

        assert "total_jobs" in stats
        assert "pending_jobs" in stats
        assert stats["total_jobs"] == 1


class TestBatchJob:
    """Tests for BatchJob dataclass."""

    def test_duration_running(self):
        """Should calculate running duration."""
        job = BatchJob(
            id="test",
            emails=[],
            status=JobStatus.RUNNING,
            started_at=time.time() - 10,  # 10 seconds ago
        )

        duration = job.duration

        assert duration >= 10

    def test_duration_completed(self):
        """Should calculate completed duration."""
        start = time.time() - 30
        end = time.time() - 10

        job = BatchJob(
            id="test",
            emails=[],
            status=JobStatus.COMPLETED,
            started_at=start,
            completed_at=end,
        )

        duration = job.duration

        assert abs(duration - 20) < 1  # ~20 seconds

    def test_to_dict(self):
        """Should convert to dictionary."""
        job = BatchJob(
            id="test-id",
            emails=[{"id": 1}],
            status=JobStatus.PENDING,
            total=1,
            processed=0,
        )

        data = job.to_dict()

        assert data["id"] == "test-id"
        assert data["status"] == "pending"
        assert data["total"] == 1


class TestProcessingMode:
    """Tests for ProcessingMode enum."""

    def test_realtime_value(self):
        """Should have realtime value."""
        assert ProcessingMode.REALTIME.value == "realtime"

    def test_batch_value(self):
        """Should have batch value."""
        assert ProcessingMode.BATCH.value == "batch"


class TestJobStatus:
    """Tests for JobStatus enum."""

    def test_all_statuses(self):
        """Should have all expected statuses."""
        statuses = [s.value for s in JobStatus]

        assert "pending" in statuses
        assert "running" in statuses
        assert "completed" in statuses
        assert "failed" in statuses
        assert "cancelled" in statuses


class TestGlobalProcessor:
    """Tests for global processor instance."""

    def setup_method(self):
        reset_processor()

    def teardown_method(self):
        reset_processor()

    def test_singleton(self):
        """Should return same instance."""
        proc1 = get_processor()
        proc2 = get_processor()

        assert proc1 is proc2
