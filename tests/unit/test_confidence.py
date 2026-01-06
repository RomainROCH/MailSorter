"""
Unit tests for confidence calibration (V5-005, INT-003).
"""

import os
import tempfile
import pytest

from backend.core.confidence import (
    ConfidenceCalibrator,
    CalibrationEntry,
    get_calibrator,
    reset_calibrator
)


class TestConfidenceCalibrator:
    """Tests for ConfidenceCalibrator."""
    
    def setup_method(self):
        """Create calibrator with temporary file."""
        self.temp_dir = tempfile.mkdtemp()
        self.calibrator = ConfidenceCalibrator({
            "calibration_file": os.path.join(self.temp_dir, "calibration.json"),
            "auto_adjust": False,
            "min_samples": 5  # Low for testing
        })
    
    def test_default_threshold(self):
        """Should return default threshold for unknown folder."""
        threshold = self.calibrator.get_threshold("UnknownFolder")
        assert threshold == 0.5
    
    def test_custom_threshold(self):
        """Should return configured threshold."""
        self.calibrator.set_threshold("Invoices", 0.85)
        assert self.calibrator.get_threshold("Invoices") == 0.85
    
    def test_builtin_thresholds(self):
        """Should have sensible built-in thresholds."""
        assert self.calibrator.get_threshold("Inbox") == 0.3
        assert self.calibrator.get_threshold("Spam") == 0.8
        assert self.calibrator.get_threshold("Trash") == 0.9
    
    def test_passes_threshold_above(self):
        """Should pass when confidence >= threshold."""
        self.calibrator.set_threshold("Test", 0.7)
        
        assert self.calibrator.passes_threshold("Test", 0.7) is True
        assert self.calibrator.passes_threshold("Test", 0.8) is True
    
    def test_passes_threshold_below(self):
        """Should not pass when confidence < threshold."""
        self.calibrator.set_threshold("Test", 0.7)
        
        assert self.calibrator.passes_threshold("Test", 0.69) is False
        assert self.calibrator.passes_threshold("Test", 0.5) is False
    
    def test_log_prediction(self):
        """Should log predictions."""
        self.calibrator.log_prediction("Invoices", 0.85)
        self.calibrator.log_prediction("Invoices", 0.9)
        
        stats = self.calibrator.get_folder_stats("Invoices")
        
        assert stats["count"] == 2
        assert stats["avg_confidence"] == 0.875
    
    def test_log_prediction_with_actual(self):
        """Should track accuracy when actual provided."""
        self.calibrator.log_prediction("Invoices", 0.85, actual_folder="Invoices")
        self.calibrator.log_prediction("Invoices", 0.6, actual_folder="Inbox")
        
        stats = self.calibrator.get_folder_stats("Invoices")
        
        assert stats["labeled_count"] == 2
        assert stats["accuracy"] == 0.5
    
    def test_record_correction(self):
        """Should record user corrections."""
        self.calibrator.record_correction(
            predicted_folder="Invoices",
            actual_folder="Inbox",
            confidence=0.7
        )
        
        stats = self.calibrator.get_folder_stats("Invoices")
        assert stats["labeled_count"] == 1
        assert stats["accuracy"] == 0.0
    
    def test_get_all_stats(self):
        """Should return stats for all folders."""
        self.calibrator.log_prediction("Invoices", 0.8)
        self.calibrator.log_prediction("Newsletters", 0.7)
        
        all_stats = self.calibrator.get_all_stats()
        
        assert "Invoices" in all_stats
        assert "Newsletters" in all_stats
    
    def test_threshold_clamp(self):
        """Should clamp threshold to valid range."""
        self.calibrator.set_threshold("Test", 1.5)
        assert self.calibrator.get_threshold("Test") == 1.0
        
        self.calibrator.set_threshold("Test", -0.5)
        assert self.calibrator.get_threshold("Test") == 0.0
    
    def test_export_calibration(self):
        """Should export calibration data."""
        self.calibrator.log_prediction("Invoices", 0.85, "Invoices")
        
        data = self.calibrator.export_calibration()
        
        assert "Invoices" in data
        assert len(data["Invoices"]) == 1
        assert data["Invoices"][0]["predicted"] == "Invoices"
    
    def test_clear_calibration(self):
        """Should clear all calibration data."""
        self.calibrator.log_prediction("Invoices", 0.85)
        self.calibrator.clear_calibration()
        
        stats = self.calibrator.get_folder_stats("Invoices")
        assert stats["count"] == 0


class TestCalibrationEntry:
    """Tests for CalibrationEntry dataclass."""
    
    def test_correct_prediction(self):
        """Should detect correct prediction."""
        entry = CalibrationEntry(
            predicted="Invoices",
            actual="Invoices",
            confidence=0.9,
            timestamp=0
        )
        assert entry.correct is True
    
    def test_incorrect_prediction(self):
        """Should detect incorrect prediction."""
        entry = CalibrationEntry(
            predicted="Invoices",
            actual="Inbox",
            confidence=0.6,
            timestamp=0
        )
        assert entry.correct is False
    
    def test_unknown_actual(self):
        """Should handle unknown actual."""
        entry = CalibrationEntry(
            predicted="Invoices",
            actual=None,
            confidence=0.8,
            timestamp=0
        )
        assert entry.correct is None


class TestGlobalCalibrator:
    """Tests for global calibrator instance."""
    
    def setup_method(self):
        reset_calibrator()
    
    def teardown_method(self):
        reset_calibrator()
    
    def test_singleton(self):
        """Should return same instance."""
        cal1 = get_calibrator()
        cal2 = get_calibrator()
        
        assert cal1 is cal2
