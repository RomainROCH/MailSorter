"""
Unit tests for Feedback Loop module.

Tests GDPR-compliant feedback collection for model fine-tuning.
"""

import json
import os
import pytest
import tempfile
import threading
import time

from backend.core.feedback_loop import (
    FeedbackLoop,
    FeedbackEntry,
    get_feedback_loop,
)


class TestFeedbackEntryDataclass:
    """Tests for FeedbackEntry dataclass."""

    def test_entry_creation(self):
        """Entry created with correct fields."""
        entry = FeedbackEntry(
            email_id="123",
            subject="Test Subject",
            body="Test body",
            predicted_folder="Inbox",
            actual_folder="Work",
            confidence=0.8,
            timestamp=time.time(),
        )

        assert entry.email_id == "123"
        assert entry.subject == "Test Subject"
        assert entry.predicted_folder == "Inbox"
        assert entry.actual_folder == "Work"

    def test_is_correct_auto_calculated(self):
        """is_correct field auto-calculated in post_init."""
        # Incorrect prediction
        entry1 = FeedbackEntry(
            email_id="1",
            subject="",
            body="",
            predicted_folder="A",
            actual_folder="B",
            confidence=0.5,
            timestamp=0,
        )
        assert entry1.is_correct is False

        # Correct prediction
        entry2 = FeedbackEntry(
            email_id="2",
            subject="",
            body="",
            predicted_folder="A",
            actual_folder="A",
            confidence=0.9,
            timestamp=0,
        )
        assert entry2.is_correct is True


class TestFeedbackLoopInit:
    """Tests for FeedbackLoop initialization."""

    def test_default_disabled(self):
        """Feedback loop disabled by default."""
        loop = FeedbackLoop()

        assert loop.is_enabled() is False

    def test_init_with_config(self):
        """Config options are respected."""
        with tempfile.TemporaryDirectory() as tmpdir:
            data_file = os.path.join(tmpdir, "feedback.json")

            loop = FeedbackLoop(
                {
                    "enabled": True,
                    "consent_given": True,
                    "min_samples": 50,
                    "max_entries": 500,
                    "data_file": data_file,
                }
            )

            assert loop.is_enabled() is True
            assert loop.min_samples == 50
            assert loop.max_entries == 500

    def test_enabled_without_consent_not_enabled(self):
        """Enabled but no consent = not enabled."""
        loop = FeedbackLoop({"enabled": True, "consent_given": False})

        assert loop.is_enabled() is False


class TestEnableDisable:
    """Tests for enable/disable functionality."""

    def test_enable_with_consent(self):
        """Can enable with consent."""
        loop = FeedbackLoop()

        loop.enable(consent=True)

        assert loop.is_enabled() is True

    def test_enable_without_consent(self):
        """Enabling without consent doesn't fully enable."""
        loop = FeedbackLoop()

        loop.enable(consent=False)

        assert loop.is_enabled() is False

    def test_disable(self):
        """Can disable feedback loop."""
        loop = FeedbackLoop({"enabled": True, "consent_given": True})

        loop.disable()

        assert loop.is_enabled() is False


class TestRecordFeedback:
    """Tests for feedback recording."""

    def test_record_when_disabled(self):
        """Recording when disabled returns False."""
        loop = FeedbackLoop()

        result = loop.record_feedback(
            email_id="1",
            subject="Test",
            body="Body",
            predicted_folder="A",
            actual_folder="B",
            confidence=0.5,
        )

        assert result is False

    def test_record_when_enabled(self):
        """Recording when enabled returns True."""
        with tempfile.TemporaryDirectory() as tmpdir:
            data_file = os.path.join(tmpdir, "feedback.json")
            loop = FeedbackLoop(
                {"enabled": True, "consent_given": True, "data_file": data_file}
            )

            result = loop.record_feedback(
                email_id="1",
                subject="Test",
                body="Body",
                predicted_folder="A",
                actual_folder="B",
                confidence=0.5,
            )

            assert result is True

    def test_record_truncates_long_subject(self):
        """Long subjects are truncated."""
        with tempfile.TemporaryDirectory() as tmpdir:
            data_file = os.path.join(tmpdir, "feedback.json")
            loop = FeedbackLoop(
                {"enabled": True, "consent_given": True, "data_file": data_file}
            )

            long_subject = "x" * 1000
            loop.record_feedback("1", long_subject, "body", "A", "B", 0.5)

            stats = loop.get_stats()
            assert stats["total_entries"] == 1

    def test_record_truncates_long_body(self):
        """Long bodies are truncated."""
        with tempfile.TemporaryDirectory() as tmpdir:
            data_file = os.path.join(tmpdir, "feedback.json")
            loop = FeedbackLoop(
                {"enabled": True, "consent_given": True, "data_file": data_file}
            )

            long_body = "x" * 5000
            loop.record_feedback("1", "subject", long_body, "A", "B", 0.5)

    def test_record_updates_stats(self):
        """Recording updates statistics."""
        with tempfile.TemporaryDirectory() as tmpdir:
            data_file = os.path.join(tmpdir, "feedback.json")
            loop = FeedbackLoop(
                {"enabled": True, "consent_given": True, "data_file": data_file}
            )

            # Record a correction
            loop.record_feedback("1", "s", "b", "A", "B", 0.5)

            # Record a confirmation
            loop.record_feedback("2", "s", "b", "C", "C", 0.9)

            stats = loop.get_stats()
            assert stats["total_entries"] == 2
            assert stats["corrections"] == 1
            assert stats["confirmations"] == 1

    def test_max_entries_enforced(self):
        """Old entries pruned when max exceeded."""
        with tempfile.TemporaryDirectory() as tmpdir:
            data_file = os.path.join(tmpdir, "feedback.json")
            loop = FeedbackLoop(
                {
                    "enabled": True,
                    "consent_given": True,
                    "data_file": data_file,
                    "max_entries": 5,
                }
            )

            for i in range(10):
                loop.record_feedback(str(i), "s", "b", "A", "B", 0.5)

            stats = loop.get_stats()
            assert stats["total_entries"] == 5


class TestGetStats:
    """Tests for statistics retrieval."""

    def test_stats_empty(self):
        """Stats for empty loop."""
        loop = FeedbackLoop()

        stats = loop.get_stats()

        assert stats["total_entries"] == 0
        assert stats["accuracy"] == 0.0
        assert stats["ready_for_export"] is False

    def test_stats_accuracy_calculation(self):
        """Accuracy calculated correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            data_file = os.path.join(tmpdir, "feedback.json")
            loop = FeedbackLoop(
                {
                    "enabled": True,
                    "consent_given": True,
                    "data_file": data_file,
                    "min_samples": 2,
                }
            )

            # 3 correct, 1 incorrect = 75% accuracy
            loop.record_feedback("1", "s", "b", "A", "A", 0.9)
            loop.record_feedback("2", "s", "b", "B", "B", 0.9)
            loop.record_feedback("3", "s", "b", "C", "C", 0.9)
            loop.record_feedback("4", "s", "b", "D", "E", 0.5)

            stats = loop.get_stats()
            assert stats["accuracy"] == 0.75

    def test_ready_for_export(self):
        """ready_for_export based on min_samples."""
        with tempfile.TemporaryDirectory() as tmpdir:
            data_file = os.path.join(tmpdir, "feedback.json")
            loop = FeedbackLoop(
                {
                    "enabled": True,
                    "consent_given": True,
                    "data_file": data_file,
                    "min_samples": 3,
                }
            )

            loop.record_feedback("1", "s", "b", "A", "B", 0.5)
            loop.record_feedback("2", "s", "b", "A", "B", 0.5)

            assert loop.get_stats()["ready_for_export"] is False

            loop.record_feedback("3", "s", "b", "A", "B", 0.5)

            assert loop.get_stats()["ready_for_export"] is True


class TestExportTrainingData:
    """Tests for training data export."""

    def test_export_not_enough_data(self):
        """Export fails with not enough data."""
        with tempfile.TemporaryDirectory() as tmpdir:
            data_file = os.path.join(tmpdir, "feedback.json")
            loop = FeedbackLoop(
                {
                    "enabled": True,
                    "consent_given": True,
                    "data_file": data_file,
                    "min_samples": 100,
                }
            )

            loop.record_feedback("1", "s", "b", "A", "B", 0.5)

            result = loop.export_training_data()

            assert result is None

    def test_export_creates_jsonl(self):
        """Export creates valid JSONL file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            data_file = os.path.join(tmpdir, "feedback.json")
            output_file = os.path.join(tmpdir, "training.jsonl")

            loop = FeedbackLoop(
                {
                    "enabled": True,
                    "consent_given": True,
                    "data_file": data_file,
                    "min_samples": 2,
                }
            )

            loop.record_feedback("1", "Subject 1", "Body 1", "A", "B", 0.5)
            loop.record_feedback("2", "Subject 2", "Body 2", "C", "C", 0.9)

            result = loop.export_training_data(output_file)

            assert result == output_file
            assert os.path.exists(output_file)

            # Verify JSONL format
            with open(output_file, "r") as f:
                lines = f.readlines()

            assert len(lines) == 2
            for line in lines:
                data = json.loads(line)
                assert "prompt" in data
                assert "response" in data

    def test_export_corrections_only(self):
        """Can export only corrections."""
        with tempfile.TemporaryDirectory() as tmpdir:
            data_file = os.path.join(tmpdir, "feedback.json")
            output_file = os.path.join(tmpdir, "training.jsonl")

            loop = FeedbackLoop(
                {
                    "enabled": True,
                    "consent_given": True,
                    "data_file": data_file,
                    "min_samples": 2,
                }
            )

            loop.record_feedback("1", "s", "b", "A", "B", 0.5)  # Correction
            loop.record_feedback("2", "s", "b", "C", "C", 0.9)  # Correct
            loop.record_feedback("3", "s", "b", "D", "E", 0.5)  # Correction

            result = loop.export_training_data(output_file, include_correct=False)

            # Should only have 2 entries (corrections only)
            with open(result, "r") as f:
                lines = f.readlines()

            assert len(lines) == 2


class TestClearData:
    """Tests for GDPR data erasure."""

    def test_clear_removes_entries(self):
        """clear_data removes all entries."""
        with tempfile.TemporaryDirectory() as tmpdir:
            data_file = os.path.join(tmpdir, "feedback.json")

            loop = FeedbackLoop(
                {"enabled": True, "consent_given": True, "data_file": data_file}
            )

            loop.record_feedback("1", "s", "b", "A", "B", 0.5)
            loop.record_feedback("2", "s", "b", "C", "D", 0.5)

            loop.clear_data()

            stats = loop.get_stats()
            assert stats["total_entries"] == 0

    def test_clear_deletes_file(self):
        """clear_data deletes data file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            data_file = os.path.join(tmpdir, "feedback.json")

            loop = FeedbackLoop(
                {"enabled": True, "consent_given": True, "data_file": data_file}
            )

            loop.record_feedback("1", "s", "b", "A", "B", 0.5)
            loop._save_data()

            assert os.path.exists(data_file)

            loop.clear_data()

            assert not os.path.exists(data_file)

    def test_clear_resets_stats(self):
        """clear_data resets statistics."""
        with tempfile.TemporaryDirectory() as tmpdir:
            data_file = os.path.join(tmpdir, "feedback.json")

            loop = FeedbackLoop(
                {"enabled": True, "consent_given": True, "data_file": data_file}
            )

            loop.record_feedback("1", "s", "b", "A", "B", 0.5)

            loop.clear_data()

            stats = loop.get_stats()
            assert stats["corrections"] == 0
            assert stats["confirmations"] == 0


class TestPersistence:
    """Tests for data persistence."""

    def test_save_and_load(self):
        """Data survives save/load cycle."""
        with tempfile.TemporaryDirectory() as tmpdir:
            data_file = os.path.join(tmpdir, "feedback.json")

            # Create and populate
            loop1 = FeedbackLoop(
                {"enabled": True, "consent_given": True, "data_file": data_file}
            )
            loop1.record_feedback("1", "Subject", "Body", "A", "B", 0.5)
            loop1._save_data()

            # Load in new instance
            loop2 = FeedbackLoop(
                {"enabled": True, "consent_given": True, "data_file": data_file}
            )

            stats = loop2.get_stats()
            assert stats["total_entries"] == 1

    def test_load_missing_file(self):
        """Loading from missing file doesn't crash."""
        with tempfile.TemporaryDirectory() as tmpdir:
            data_file = os.path.join(tmpdir, "nonexistent.json")

            loop = FeedbackLoop(
                {"enabled": True, "consent_given": True, "data_file": data_file}
            )

            stats = loop.get_stats()
            assert stats["total_entries"] == 0

    def test_load_corrupted_file(self):
        """Loading corrupted file doesn't crash."""
        with tempfile.TemporaryDirectory() as tmpdir:
            data_file = os.path.join(tmpdir, "feedback.json")

            # Write corrupted data
            with open(data_file, "w") as f:
                f.write("not valid json{{{")

            loop = FeedbackLoop(
                {"enabled": True, "consent_given": True, "data_file": data_file}
            )

            stats = loop.get_stats()
            assert stats["total_entries"] == 0


class TestCorrectionPatterns:
    """Tests for correction pattern analysis."""

    def test_get_correction_patterns(self):
        """Correction patterns correctly aggregated."""
        with tempfile.TemporaryDirectory() as tmpdir:
            data_file = os.path.join(tmpdir, "feedback.json")

            loop = FeedbackLoop(
                {"enabled": True, "consent_given": True, "data_file": data_file}
            )

            # Predicted Inbox, but user put in Work (twice)
            loop.record_feedback("1", "s", "b", "Inbox", "Work", 0.5)
            loop.record_feedback("2", "s", "b", "Inbox", "Work", 0.5)

            # Predicted Inbox, but user put in Personal
            loop.record_feedback("3", "s", "b", "Inbox", "Personal", 0.5)

            patterns = loop.get_correction_patterns()

            assert "Inbox" in patterns
            assert patterns["Inbox"]["Work"] == 2
            assert patterns["Inbox"]["Personal"] == 1

    def test_correct_predictions_not_in_patterns(self):
        """Correct predictions not included in patterns."""
        with tempfile.TemporaryDirectory() as tmpdir:
            data_file = os.path.join(tmpdir, "feedback.json")

            loop = FeedbackLoop(
                {"enabled": True, "consent_given": True, "data_file": data_file}
            )

            # Correct prediction
            loop.record_feedback("1", "s", "b", "Inbox", "Inbox", 0.9)

            patterns = loop.get_correction_patterns()

            assert len(patterns) == 0


class TestThreadSafety:
    """Tests for thread-safe operation."""

    @pytest.mark.timeout(5)
    def test_concurrent_recording(self):
        """Multiple threads can record concurrently."""
        with tempfile.TemporaryDirectory() as tmpdir:
            data_file = os.path.join(tmpdir, "feedback.json")

            loop = FeedbackLoop(
                {
                    "enabled": True,
                    "consent_given": True,
                    "data_file": data_file,
                    "max_entries": 10000,
                }
            )

            errors = []

            def worker(start_id):
                try:
                    for i in range(100):
                        loop.record_feedback(f"{start_id}-{i}", "s", "b", "A", "B", 0.5)
                except Exception as e:
                    errors.append(e)

            threads = [threading.Thread(target=worker, args=(i,)) for i in range(5)]
            for t in threads:
                t.start()
            for t in threads:
                t.join()

            assert len(errors) == 0
            stats = loop.get_stats()
            assert stats["total_entries"] == 500


class TestGlobalFeedbackLoop:
    """Tests for global singleton."""

    def test_get_feedback_loop_singleton(self):
        """get_feedback_loop returns same instance."""
        import backend.core.feedback_loop as module

        module._feedback_loop = None  # Reset

        loop1 = get_feedback_loop()
        loop2 = get_feedback_loop()

        assert loop1 is loop2


class TestFormatTrainingExample:
    """Tests for training example formatting."""

    def test_format_includes_prompt_and_response(self):
        """Formatted example has required fields."""
        with tempfile.TemporaryDirectory() as tmpdir:
            data_file = os.path.join(tmpdir, "feedback.json")

            loop = FeedbackLoop(
                {"enabled": True, "consent_given": True, "data_file": data_file}
            )

            entry = FeedbackEntry(
                email_id="1",
                subject="Test Subject",
                body="Test body content",
                predicted_folder="Inbox",
                actual_folder="Work",
                confidence=0.5,
                timestamp=time.time(),
            )

            formatted = loop._format_training_example(entry)

            assert "prompt" in formatted
            assert "response" in formatted
            assert "source" in formatted
            assert formatted["source"] == "user_feedback"

            # Response should be JSON with actual folder
            response = json.loads(formatted["response"])
            assert response["folder"] == "Work"
