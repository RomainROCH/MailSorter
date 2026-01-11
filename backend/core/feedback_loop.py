"""
Feedback loop for Ollama local fine-tuning.

Implements V5-008: Opt-in user feedback collection for model improvement.
Collects corrections and can export data for fine-tuning.

GDPR Considerations:
- Explicit user consent required
- Data stored locally only
- Clear data on user request
- No PII in training data (sanitized)
"""

import json
import logging
import os
import threading
import time
from dataclasses import dataclass
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class FeedbackEntry:
    """A single user feedback entry."""

    email_id: str
    subject: str  # Sanitized
    body: str  # Sanitized, truncated
    predicted_folder: str
    actual_folder: str
    confidence: float
    timestamp: float
    is_correct: bool = False

    def __post_init__(self):
        self.is_correct = self.predicted_folder == self.actual_folder


class FeedbackLoop:
    """
    Feedback collection for model improvement.

    Features:
    - Collects user corrections (when they move emails differently)
    - Stores sanitized data locally
    - Exports data in JSONL format for fine-tuning
    - GDPR-compliant with explicit consent

    Usage:
        loop = FeedbackLoop(config)

        # Check consent
        if not loop.is_enabled():
            return

        # Record feedback when user moves email
        loop.record_feedback(
            email_id="123",
            subject="Invoice #456",
            body="Payment details...",
            predicted_folder="Inbox",
            actual_folder="Invoices",
            confidence=0.6
        )

        # Export for fine-tuning
        loop.export_training_data("training.jsonl")
    """

    def __init__(self, config: Optional[Dict] = None):
        """
        Initialize feedback loop.

        Args:
            config: Configuration with:
                - enabled: Enable feedback collection (default: False)
                - consent_given: User has given consent (default: False)
                - min_samples: Minimum samples before export (default: 100)
                - data_file: Path to feedback data file
                - max_entries: Maximum entries to keep (default: 10000)
        """
        config = config or {}

        self._enabled = config.get("enabled", False)
        self._consent_given = config.get("consent_given", False)
        self.min_samples = config.get("min_samples", 100)
        self.max_entries = config.get("max_entries", 10000)

        # Data storage path
        self.data_file = config.get(
            "data_file", os.path.expanduser("~/.mailsorter/feedback.json")
        )

        # In-memory feedback storage
        self._entries: List[FeedbackEntry] = []
        self._lock = threading.Lock()

        # Statistics
        self._stats = {"total_feedback": 0, "corrections": 0, "confirmations": 0}

        # Load existing data
        self._load_data()

    def is_enabled(self) -> bool:
        """Check if feedback collection is enabled and consented."""
        return self._enabled and self._consent_given

    def enable(self, consent: bool = True) -> None:
        """
        Enable feedback collection.

        Args:
            consent: User has given explicit consent
        """
        self._enabled = True
        self._consent_given = consent
        logger.info(f"Feedback loop enabled (consent: {consent})")

    def disable(self) -> None:
        """Disable feedback collection."""
        self._enabled = False
        logger.info("Feedback loop disabled")

    def record_feedback(
        self,
        email_id: str,
        subject: str,
        body: str,
        predicted_folder: str,
        actual_folder: str,
        confidence: float,
    ) -> bool:
        """
        Record user feedback.

        Args:
            email_id: Email identifier
            subject: Email subject (should be sanitized)
            body: Email body (should be sanitized)
            predicted_folder: What the model predicted
            actual_folder: Where the user actually put it
            confidence: Original confidence score

        Returns:
            True if feedback was recorded
        """
        if not self.is_enabled():
            return False

        entry = FeedbackEntry(
            email_id=email_id,
            subject=subject[:500],  # Truncate
            body=body[:1500],  # Truncate
            predicted_folder=predicted_folder,
            actual_folder=actual_folder,
            confidence=confidence,
            timestamp=time.time(),
        )

        with self._lock:
            self._entries.append(entry)
            self._stats["total_feedback"] += 1

            if entry.is_correct:
                self._stats["confirmations"] += 1
            else:
                self._stats["corrections"] += 1

            # Prune old entries if needed
            if len(self._entries) > self.max_entries:
                self._entries = self._entries[-self.max_entries :]

            # Auto-save periodically
            if len(self._entries) % 50 == 0:
                self._save_data()

        logger.debug(
            f"Recorded feedback: {predicted_folder} → {actual_folder} "
            f"(correct: {entry.is_correct})"
        )

        return True

    def get_stats(self) -> Dict:
        """Get feedback statistics."""
        with self._lock:
            total = len(self._entries)
            corrections = sum(1 for e in self._entries if not e.is_correct)

            accuracy = 0.0
            if total > 0:
                accuracy = (total - corrections) / total

            return {
                "enabled": self.is_enabled(),
                "total_entries": total,
                "corrections": corrections,
                "confirmations": total - corrections,
                "accuracy": round(accuracy, 3),
                "ready_for_export": total >= self.min_samples,
                "min_samples": self.min_samples,
            }

    def export_training_data(
        self, output_file: Optional[str] = None, include_correct: bool = True
    ) -> Optional[str]:
        """
        Export feedback data for fine-tuning.

        Exports in JSONL format suitable for Ollama fine-tuning.

        Args:
            output_file: Output file path (default: auto-generated)
            include_correct: Include correct predictions (default: True)

        Returns:
            Path to exported file, or None if not enough data
        """
        with self._lock:
            if len(self._entries) < self.min_samples:
                logger.warning(
                    f"Not enough data for export: "
                    f"{len(self._entries)}/{self.min_samples}"
                )
                return None

            entries = self._entries.copy()

        # Filter entries
        if not include_correct:
            entries = [e for e in entries if not e.is_correct]

        if not entries:
            return None

        # Generate output path
        if output_file is None:
            output_dir = os.path.dirname(self.data_file)
            output_file = os.path.join(
                output_dir, f"training_data_{int(time.time())}.jsonl"
            )

        # Ensure directory exists
        os.makedirs(os.path.dirname(output_file), exist_ok=True)

        # Write JSONL format for fine-tuning
        try:
            with open(output_file, "w", encoding="utf-8") as f:
                for entry in entries:
                    training_example = self._format_training_example(entry)
                    f.write(json.dumps(training_example) + "\n")

            logger.info(f"Exported {len(entries)} training examples to {output_file}")
            return output_file

        except Exception as e:
            logger.error(f"Failed to export training data: {e}")
            return None

    def _format_training_example(self, entry: FeedbackEntry) -> Dict:
        """
        Format an entry as a training example.

        Uses the format expected by Ollama fine-tuning.
        """
        # Build the prompt
        prompt = f"""Classify this email into one folder.

Email Subject: {entry.subject}
Email Body: {entry.body[:500]}

Respond with JSON: {{"folder": "...", "confidence": 0.9}}"""

        # Build the expected response
        response = json.dumps({"folder": entry.actual_folder, "confidence": 0.95})

        return {"prompt": prompt, "response": response, "source": "user_feedback"}

    def clear_data(self) -> None:
        """
        Clear all feedback data.

        Called when user requests data deletion (GDPR right to erasure).
        """
        with self._lock:
            self._entries.clear()
            self._stats = {"total_feedback": 0, "corrections": 0, "confirmations": 0}

        # Delete data file
        try:
            if os.path.exists(self.data_file):
                os.remove(self.data_file)
        except Exception as e:
            logger.warning(f"Failed to delete feedback file: {e}")

        logger.info("Feedback data cleared")

    def _load_data(self) -> None:
        """Load feedback data from file."""
        try:
            if os.path.exists(self.data_file):
                with open(self.data_file, "r", encoding="utf-8") as f:
                    data = json.load(f)

                self._entries = [FeedbackEntry(**e) for e in data.get("entries", [])]
                self._stats = data.get("stats", self._stats)

                logger.debug(f"Loaded {len(self._entries)} feedback entries")
        except Exception as e:
            logger.warning(f"Failed to load feedback data: {e}")

    def _save_data(self) -> None:
        """Save feedback data to file."""
        try:
            os.makedirs(os.path.dirname(self.data_file), exist_ok=True)

            data = {
                "entries": [
                    {
                        "email_id": e.email_id,
                        "subject": e.subject,
                        "body": e.body,
                        "predicted_folder": e.predicted_folder,
                        "actual_folder": e.actual_folder,
                        "confidence": e.confidence,
                        "timestamp": e.timestamp,
                    }
                    for e in self._entries
                ],
                "stats": self._stats,
            }

            with open(self.data_file, "w", encoding="utf-8") as f:
                json.dump(data, f)

        except Exception as e:
            logger.warning(f"Failed to save feedback data: {e}")

    def get_correction_patterns(self) -> Dict[str, Dict[str, int]]:
        """
        Analyze correction patterns.

        Returns a dict showing predicted → actual mappings.
        Useful for identifying systematic errors.
        """
        patterns: Dict[str, Dict[str, int]] = {}

        with self._lock:
            for entry in self._entries:
                if not entry.is_correct:
                    if entry.predicted_folder not in patterns:
                        patterns[entry.predicted_folder] = {}

                    actual = entry.actual_folder
                    patterns[entry.predicted_folder][actual] = (
                        patterns[entry.predicted_folder].get(actual, 0) + 1
                    )

        return patterns


# Global feedback loop instance
_feedback_loop: Optional[FeedbackLoop] = None
_loop_lock = threading.Lock()


def get_feedback_loop(config: Optional[Dict] = None) -> FeedbackLoop:
    """
    Get or create the global feedback loop.

    Args:
        config: Optional configuration dict

    Returns:
        Global FeedbackLoop instance
    """
    global _feedback_loop

    with _loop_lock:
        if _feedback_loop is None:
            _feedback_loop = FeedbackLoop(config)
        return _feedback_loop
