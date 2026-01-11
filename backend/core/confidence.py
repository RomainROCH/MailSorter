"""
Confidence score calibration and dynamic thresholds.

Implements:
- V5-005: Dynamic thresholds per folder
- INT-003: Confidence score calibration with logging and auto-adjust
"""

import json
import logging
import os
import threading
import time
from collections import defaultdict
from dataclasses import dataclass
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class CalibrationEntry:
    """A single calibration data point."""

    predicted: str
    actual: Optional[str]
    confidence: float
    timestamp: float
    correct: Optional[bool] = None

    def __post_init__(self):
        if self.actual is not None:
            self.correct = self.predicted == self.actual


class ConfidenceCalibrator:
    """
    Confidence score calibration and dynamic threshold management.

    Features:
    - Per-folder confidence thresholds
    - Calibration data logging for analysis
    - Auto-adjustment based on historical accuracy
    - Persistence to local file

    Usage:
        calibrator = ConfidenceCalibrator(config)

        # Check if classification should be applied
        if calibrator.passes_threshold("Invoices", 0.85):
            apply_classification()

        # Log for calibration
        calibrator.log_prediction("Invoices", 0.85, actual_folder="Invoices")
    """

    # Default thresholds for common folder types
    DEFAULT_THRESHOLDS = {
        "Inbox": 0.3,  # Very low threshold for Inbox (default folder)
        "Spam": 0.8,  # High threshold for Spam (destructive)
        "Trash": 0.9,  # Very high threshold for Trash
        "Archive": 0.6,  # Medium threshold for Archive
    }

    DEFAULT_THRESHOLD = 0.5

    def __init__(self, config: Optional[Dict] = None):
        """
        Initialize confidence calibrator.

        Args:
            config: Configuration with:
                - thresholds: Dict of folder → threshold
                - default_threshold: Default threshold (0.5)
                - calibration_file: Path to calibration data file
                - auto_adjust: Enable automatic threshold adjustment
                - min_samples: Minimum samples before auto-adjust (50)
        """
        config = config or {}

        # Per-folder thresholds
        self.thresholds = {**self.DEFAULT_THRESHOLDS}
        self.thresholds.update(config.get("thresholds", {}))
        self.default_threshold = config.get("default_threshold", self.DEFAULT_THRESHOLD)

        # Calibration settings
        self.auto_adjust = config.get("auto_adjust", False)
        self.min_samples = config.get("min_samples", 50)

        # Calibration data storage
        self.calibration_file = config.get(
            "calibration_file", os.path.expanduser("~/.mailsorter/calibration.json")
        )

        # In-memory calibration data
        self._predictions: Dict[str, List[CalibrationEntry]] = defaultdict(list)
        self._lock = threading.Lock()

        # Load existing calibration data
        self._load_calibration()

    def get_threshold(self, folder: str) -> float:
        """
        Get confidence threshold for a folder.

        Args:
            folder: Folder name

        Returns:
            Threshold value (0.0 to 1.0)
        """
        return self.thresholds.get(folder, self.default_threshold)

    def set_threshold(self, folder: str, threshold: float) -> None:
        """
        Set confidence threshold for a folder.

        Args:
            folder: Folder name
            threshold: Threshold value (0.0 to 1.0)
        """
        threshold = max(0.0, min(1.0, threshold))
        self.thresholds[folder] = threshold
        logger.debug(f"Set threshold for '{folder}': {threshold}")

    def passes_threshold(self, folder: str, confidence: float) -> bool:
        """
        Check if confidence meets the folder's threshold.

        Args:
            folder: Target folder
            confidence: Classification confidence

        Returns:
            True if classification should be applied
        """
        threshold = self.get_threshold(folder)
        passes = confidence >= threshold

        if not passes:
            logger.debug(
                f"Confidence {confidence:.2f} below threshold {threshold:.2f} for '{folder}'"
            )

        return passes

    def log_prediction(
        self,
        predicted_folder: str,
        confidence: float,
        actual_folder: Optional[str] = None,
    ) -> None:
        """
        Log a prediction for calibration.

        Args:
            predicted_folder: The folder predicted by LLM
            confidence: The confidence score
            actual_folder: The actual correct folder (if known, e.g., user correction)
        """
        entry = CalibrationEntry(
            predicted=predicted_folder,
            actual=actual_folder,
            confidence=confidence,
            timestamp=time.time(),
        )

        with self._lock:
            self._predictions[predicted_folder].append(entry)

            # Auto-save periodically
            total = sum(len(v) for v in self._predictions.values())
            if total % 100 == 0:
                self._save_calibration()

            # Auto-adjust thresholds if enabled
            if self.auto_adjust and actual_folder is not None:
                self._maybe_auto_adjust(predicted_folder)

    def record_correction(
        self, predicted_folder: str, actual_folder: str, confidence: float
    ) -> None:
        """
        Record a user correction for calibration.

        This is called when the user manually moves an email
        that was auto-classified, indicating the prediction was wrong.

        Args:
            predicted_folder: What the LLM predicted
            actual_folder: Where the user moved it
            confidence: The original confidence score
        """
        self.log_prediction(predicted_folder, confidence, actual_folder)
        logger.info(
            f"Recorded correction: {predicted_folder} → {actual_folder} "
            f"(confidence was {confidence:.2f})"
        )

    def get_folder_stats(self, folder: str) -> Dict:
        """
        Get calibration statistics for a folder.

        Args:
            folder: Folder name

        Returns:
            Dict with accuracy, average confidence, count, etc.
        """
        with self._lock:
            entries = self._predictions.get(folder, [])

        if not entries:
            return {
                "folder": folder,
                "count": 0,
                "accuracy": None,
                "avg_confidence": None,
                "threshold": self.get_threshold(folder),
                "recommended_threshold": None,
            }

        # Filter entries with known actual values
        labeled = [e for e in entries if e.actual is not None]

        # Calculate metrics
        avg_confidence = sum(e.confidence for e in entries) / len(entries)

        accuracy = None
        if labeled:
            correct = sum(1 for e in labeled if e.correct)
            accuracy = correct / len(labeled)

        return {
            "folder": folder,
            "count": len(entries),
            "labeled_count": len(labeled),
            "accuracy": accuracy,
            "avg_confidence": avg_confidence,
            "threshold": self.get_threshold(folder),
            "recommended_threshold": self._recommend_threshold(entries),
        }

    def get_all_stats(self) -> Dict[str, Dict]:
        """Get calibration statistics for all folders."""
        with self._lock:
            folders = list(self._predictions.keys())

        return {folder: self.get_folder_stats(folder) for folder in folders}

    def _recommend_threshold(self, entries: List[CalibrationEntry]) -> Optional[float]:
        """
        Calculate recommended threshold based on calibration data.

        Strategy: Find threshold that maximizes accuracy while
        minimizing false positives. Uses 95th percentile of
        incorrect predictions as a starting point.
        """
        if len(entries) < self.min_samples:
            return None

        labeled = [e for e in entries if e.actual is not None]
        if len(labeled) < self.min_samples // 2:
            return None

        # Get confidence of incorrect predictions
        incorrect = [e.confidence for e in labeled if not e.correct]

        if not incorrect:
            # All correct! Use lower threshold
            return max(0.3, min(e.confidence for e in labeled) - 0.1)

        # Use 95th percentile of incorrect as threshold
        incorrect.sort()
        idx = int(len(incorrect) * 0.95)
        threshold = min(incorrect[idx] + 0.05, 0.95)

        return round(threshold, 2)

    def _maybe_auto_adjust(self, folder: str) -> None:
        """Auto-adjust threshold if enough data and enabled."""
        stats = self.get_folder_stats(folder)

        if stats["count"] >= self.min_samples and stats["recommended_threshold"]:
            old_threshold = self.get_threshold(folder)
            new_threshold = stats["recommended_threshold"]

            # Only adjust if significantly different
            if abs(new_threshold - old_threshold) >= 0.05:
                self.set_threshold(folder, new_threshold)
                logger.info(
                    f"Auto-adjusted threshold for '{folder}': "
                    f"{old_threshold:.2f} → {new_threshold:.2f}"
                )

    def auto_adjust_all(self) -> Dict[str, float]:
        """
        Auto-adjust thresholds for all folders with enough data.

        Returns:
            Dict of folder → new threshold for adjusted folders
        """
        adjusted = {}

        for folder in list(self._predictions.keys()):
            stats = self.get_folder_stats(folder)
            if stats["count"] >= self.min_samples and stats["recommended_threshold"]:
                old = self.get_threshold(folder)
                new = stats["recommended_threshold"]
                if abs(new - old) >= 0.05:
                    self.set_threshold(folder, new)
                    adjusted[folder] = new

        if adjusted:
            logger.info(f"Auto-adjusted thresholds: {adjusted}")

        return adjusted

    def _load_calibration(self) -> None:
        """Load calibration data from file."""
        try:
            if os.path.exists(self.calibration_file):
                with open(self.calibration_file, "r", encoding="utf-8") as f:
                    data = json.load(f)

                for folder, entries in data.items():
                    self._predictions[folder] = [CalibrationEntry(**e) for e in entries]

                total = sum(len(v) for v in self._predictions.values())
                logger.debug(f"Loaded {total} calibration entries")
        except Exception as e:
            logger.warning(f"Failed to load calibration data: {e}")

    def _save_calibration(self) -> None:
        """Save calibration data to file."""
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(self.calibration_file), exist_ok=True)

            # Keep only last 1000 entries per folder
            data = {}
            for folder, entries in self._predictions.items():
                recent = entries[-1000:]
                data[folder] = [
                    {
                        "predicted": e.predicted,
                        "actual": e.actual,
                        "confidence": e.confidence,
                        "timestamp": e.timestamp,
                    }
                    for e in recent
                ]

            with open(self.calibration_file, "w", encoding="utf-8") as f:
                json.dump(data, f)

            logger.debug(f"Saved calibration data to {self.calibration_file}")
        except Exception as e:
            logger.warning(f"Failed to save calibration data: {e}")

    def export_calibration(self) -> Dict:
        """Export calibration data for analysis."""
        with self._lock:
            return {
                folder: [
                    {
                        "predicted": e.predicted,
                        "actual": e.actual,
                        "confidence": e.confidence,
                        "timestamp": e.timestamp,
                        "correct": e.correct,
                    }
                    for e in entries
                ]
                for folder, entries in self._predictions.items()
            }

    def clear_calibration(self) -> None:
        """Clear all calibration data."""
        with self._lock:
            self._predictions.clear()

        # Also remove file
        try:
            if os.path.exists(self.calibration_file):
                os.remove(self.calibration_file)
        except Exception:
            pass

        logger.info("Calibration data cleared")


# Global calibrator instance
_calibrator: Optional[ConfidenceCalibrator] = None
_calibrator_lock = threading.Lock()


def get_calibrator(config: Optional[Dict] = None) -> ConfidenceCalibrator:
    """
    Get or create the global confidence calibrator.

    Args:
        config: Optional configuration dict

    Returns:
        Global ConfidenceCalibrator instance
    """
    global _calibrator

    with _calibrator_lock:
        if _calibrator is None:
            _calibrator = ConfidenceCalibrator(config)
        return _calibrator


def reset_calibrator() -> None:
    """Reset the global calibrator (mainly for testing)."""
    global _calibrator
    with _calibrator_lock:
        _calibrator = None
