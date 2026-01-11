"""
Unit tests for Attachment Heuristic module.

Tests security scoring based on attachment metadata.
"""

import pytest

from backend.core.attachment_heuristic import (
    AttachmentHeuristic,
    compute_file_hash,
    SUSPICIOUS_EXTENSIONS,
    SUSPICIOUS_MIME_TYPES,
    SAFE_MIME_TYPES,
)


class TestAttachmentHeuristicBasics:
    """Basic heuristic functionality tests."""
    
    def test_init(self):
        """Heuristic initializes with correct data."""
        heuristic = AttachmentHeuristic()
        
        assert len(heuristic.suspicious_extensions) > 0
        assert ".exe" in heuristic.suspicious_extensions
        assert len(heuristic.suspicious_mime_types) > 0
        assert len(heuristic.safe_mime_types) > 0
    
    def test_safe_attachment(self):
        """Safe attachment has low risk score."""
        heuristic = AttachmentHeuristic()
        
        result = heuristic.analyze_attachment(
            filename="document.pdf",
            mime_type="application/pdf",
            size_bytes=50000
        )
        
        assert result["risk_level"] == "low"
        assert result["score_adjustment"] <= 0  # Safe or neutral


class TestSuspiciousExtensions:
    """Tests for suspicious file extension detection."""
    
    @pytest.mark.parametrize("ext", [".exe", ".scr", ".bat", ".vbs", ".ps1"])
    def test_executable_extensions_flagged(self, ext):
        """Executable extensions are flagged as suspicious."""
        heuristic = AttachmentHeuristic()
        
        result = heuristic.analyze_attachment(
            filename=f"file{ext}",
            mime_type="application/octet-stream",
            size_bytes=1000
        )
        
        assert result["risk_level"] in ("high", "medium")
        assert result["score_adjustment"] > 0
        assert any("suspicious_extension" in flag for flag in result["flags"])
    
    @pytest.mark.parametrize("ext", [".docm", ".xlsm", ".pptm"])
    def test_macro_enabled_office_flagged(self, ext):
        """Macro-enabled Office documents are flagged."""
        heuristic = AttachmentHeuristic()
        
        result = heuristic.analyze_attachment(
            filename=f"document{ext}",
            mime_type="application/octet-stream"
        )
        
        assert result["risk_level"] == "high"
        assert result["score_adjustment"] > 0
    
    def test_double_extension_attack(self):
        """Double extensions (file.pdf.exe) are detected."""
        heuristic = AttachmentHeuristic()
        
        result = heuristic.analyze_attachment(
            filename="invoice.pdf.exe",
            mime_type="application/octet-stream"
        )
        
        assert "double_extension" in result["flags"]
        assert result["risk_level"] == "high"
        assert result["score_adjustment"] >= 0.4
    
    def test_double_extension_various_combos(self):
        """Various double extension attacks detected."""
        heuristic = AttachmentHeuristic()
        
        attacks = [
            "photo.jpg.scr",
            "report.doc.exe",
            "data.xlsx.bat",
        ]
        
        for filename in attacks:
            result = heuristic.analyze_attachment(filename, "application/octet-stream")
            assert "double_extension" in result["flags"], f"Failed for {filename}"
    
    def test_normal_multiple_dots_not_flagged(self):
        """Normal filenames with dots aren't false positives."""
        heuristic = AttachmentHeuristic()
        
        # These are normal and should NOT trigger double extension
        normal_files = [
            "file.backup.pdf",
            "report.2024.docx",
        ]
        
        for filename in normal_files:
            result = heuristic.analyze_attachment(filename, "application/pdf")
            assert "double_extension" not in result["flags"]


class TestMIMETypeDetection:
    """Tests for MIME type analysis."""
    
    def test_suspicious_mime_type(self):
        """Suspicious MIME types are flagged."""
        heuristic = AttachmentHeuristic()
        
        result = heuristic.analyze_attachment(
            filename="unknown",
            mime_type="application/x-msdownload"
        )
        
        assert any("suspicious_mime" in flag for flag in result["flags"])
        assert result["score_adjustment"] > 0
    
    def test_safe_mime_type_reduces_score(self):
        """Safe MIME types reduce suspicion score."""
        heuristic = AttachmentHeuristic()
        
        result = heuristic.analyze_attachment(
            filename="photo.jpg",
            mime_type="image/jpeg"
        )
        
        assert "safe_mime_type" in result["flags"]
        assert result["score_adjustment"] < 0  # Negative = safer
    
    def test_mime_extension_mismatch(self):
        """MIME/extension mismatch is flagged."""
        heuristic = AttachmentHeuristic()
        
        # PDF extension but image MIME type
        result = heuristic.analyze_attachment(
            filename="document.pdf",
            mime_type="image/jpeg"
        )
        
        assert "mime_extension_mismatch" in result["flags"]
        assert result["score_adjustment"] > 0


class TestSizeAnalysis:
    """Tests for file size analysis."""
    
    def test_small_executable_suspicious(self):
        """Very small executables are flagged."""
        heuristic = AttachmentHeuristic()
        
        result = heuristic.analyze_attachment(
            filename="tiny.exe",
            mime_type="application/octet-stream",
            size_bytes=5000  # 5KB executable is suspicious
        )
        
        assert "suspiciously_small_executable" in result["flags"]
    
    def test_normal_sized_executable_not_extra_flagged(self):
        """Normal-sized executables don't get extra size flag."""
        heuristic = AttachmentHeuristic()
        
        result = heuristic.analyze_attachment(
            filename="installer.exe",
            mime_type="application/octet-stream",
            size_bytes=5_000_000  # 5MB is normal
        )
        
        assert "suspiciously_small_executable" not in result["flags"]


class TestKnownMalwareHashes:
    """Tests for malware hash detection."""
    
    def test_known_malware_hash_critical(self):
        """Known malware hash triggers critical risk."""
        heuristic = AttachmentHeuristic()
        
        # Add a test hash to the set
        from backend.core import attachment_heuristic
        test_hash = "abc123deadbeef"
        attachment_heuristic.KNOWN_MALWARE_HASHES.add(test_hash)
        
        try:
            result = heuristic.analyze_attachment(
                filename="safe.pdf",
                mime_type="application/pdf",
                content_hash=test_hash
            )
            
            assert result["risk_level"] == "critical"
            assert "known_malware_hash" in result["flags"]
            # Score for malware hash is +0.9 but safe PDF is -0.1, net = 0.8
            assert result["score_adjustment"] >= 0.7
        finally:
            attachment_heuristic.KNOWN_MALWARE_HASHES.discard(test_hash)
    
    def test_unknown_hash_no_flag(self):
        """Unknown hash doesn't add flag."""
        heuristic = AttachmentHeuristic()
        
        result = heuristic.analyze_attachment(
            filename="document.pdf",
            mime_type="application/pdf",
            content_hash="somehash123"
        )
        
        assert "known_malware_hash" not in result["flags"]


class TestAnalyzeMultipleAttachments:
    """Tests for batch attachment analysis."""
    
    def test_no_attachments(self):
        """Empty attachment list handled."""
        heuristic = AttachmentHeuristic()
        
        result = heuristic.analyze_attachments([])
        
        assert result["total_attachments"] == 0
        assert result["aggregate_score_adjustment"] == 0.0
        assert result["highest_risk"] == "none"
    
    def test_single_safe_attachment(self):
        """Single safe attachment analysis."""
        heuristic = AttachmentHeuristic()
        
        result = heuristic.analyze_attachments([
            {"filename": "doc.pdf", "mime_type": "application/pdf", "size_bytes": 1000}
        ])
        
        assert result["total_attachments"] == 1
        assert result["highest_risk"] == "low"
    
    def test_multiple_attachments_worst_risk(self):
        """Aggregate uses worst risk level."""
        heuristic = AttachmentHeuristic()
        
        result = heuristic.analyze_attachments([
            {"filename": "doc.pdf", "mime_type": "application/pdf"},
            {"filename": "virus.exe", "mime_type": "application/octet-stream"},
        ])
        
        assert result["highest_risk"] == "high"
        assert result["aggregate_score_adjustment"] > 0
    
    def test_multiple_high_risk_bonus_penalty(self):
        """Multiple high-risk attachments add bonus penalty."""
        heuristic = AttachmentHeuristic()
        
        result = heuristic.analyze_attachments([
            {"filename": "virus1.exe", "mime_type": "application/octet-stream"},
            {"filename": "virus2.scr", "mime_type": "application/octet-stream"},
            {"filename": "virus3.bat", "mime_type": "application/octet-stream"},
        ])
        
        # Should have extra penalty for multiple high-risk
        assert result["aggregate_score_adjustment"] > 0.3


class TestScoreAdjustmentClamping:
    """Tests for score clamping behavior."""
    
    def test_score_not_below_minimum(self):
        """Score adjustment doesn't go below -0.5."""
        heuristic = AttachmentHeuristic()
        
        # Even with multiple safe indicators
        result = heuristic.analyze_attachment(
            filename="safe.jpg",
            mime_type="image/jpeg",
            size_bytes=100000
        )
        
        assert result["score_adjustment"] >= -0.5
    
    def test_score_not_above_maximum(self):
        """Score adjustment doesn't exceed 0.9."""
        heuristic = AttachmentHeuristic()
        
        # Even with all possible red flags
        from backend.core import attachment_heuristic
        test_hash = "malwarehash"
        attachment_heuristic.KNOWN_MALWARE_HASHES.add(test_hash)
        
        try:
            result = heuristic.analyze_attachment(
                filename="invoice.pdf.exe",
                mime_type="application/x-msdownload",
                size_bytes=100,
                content_hash=test_hash
            )
            
            assert result["score_adjustment"] <= 0.9
        finally:
            attachment_heuristic.KNOWN_MALWARE_HASHES.discard(test_hash)


class TestHelperFunctions:
    """Tests for internal helper methods."""
    
    def test_get_extension(self):
        """Extension extraction works."""
        heuristic = AttachmentHeuristic()
        
        assert heuristic._get_extension("file.pdf") == ".pdf"
        assert heuristic._get_extension("file.tar.gz") == ".gz"
        assert heuristic._get_extension("noextension") == ""
        assert heuristic._get_extension("") == ""
    
    def test_has_double_extension_detection(self):
        """Double extension detection works."""
        heuristic = AttachmentHeuristic()
        
        assert heuristic._has_double_extension("file.pdf.exe") is True
        assert heuristic._has_double_extension("file.doc.scr") is True
        assert heuristic._has_double_extension("file.pdf") is False
        assert heuristic._has_double_extension("file") is False
        assert heuristic._has_double_extension("") is False
    
    def test_has_mime_mismatch_detection(self):
        """MIME mismatch detection works."""
        heuristic = AttachmentHeuristic()
        
        # Mismatch cases
        assert heuristic._has_mime_mismatch("file.pdf", "image/jpeg") is True
        assert heuristic._has_mime_mismatch("file.jpg", "application/pdf") is True
        
        # Valid cases
        assert heuristic._has_mime_mismatch("file.pdf", "application/pdf") is False
        assert heuristic._has_mime_mismatch("file.jpg", "image/jpeg") is False
        
        # Edge cases
        assert heuristic._has_mime_mismatch("", "") is False
        assert heuristic._has_mime_mismatch("file.unknown", "application/unknown") is False


class TestComputeFileHash:
    """Tests for file hash computation."""
    
    def test_compute_hash(self):
        """Hash computation returns hex string."""
        content = b"test content"
        hash_result = compute_file_hash(content)
        
        assert len(hash_result) == 64  # SHA256 = 64 hex chars
        assert all(c in "0123456789abcdef" for c in hash_result)
    
    def test_hash_deterministic(self):
        """Same content produces same hash."""
        content = b"deterministic test"
        
        hash1 = compute_file_hash(content)
        hash2 = compute_file_hash(content)
        
        assert hash1 == hash2
    
    def test_hash_different_for_different_content(self):
        """Different content produces different hashes."""
        hash1 = compute_file_hash(b"content1")
        hash2 = compute_file_hash(b"content2")
        
        assert hash1 != hash2


class TestExtensionDataSets:
    """Tests for the extension/MIME type data sets."""
    
    def test_suspicious_extensions_lowercase(self):
        """Suspicious extensions are lowercase with dot."""
        for ext in SUSPICIOUS_EXTENSIONS:
            assert ext.startswith("."), f"Extension should start with dot: {ext}"
            assert ext == ext.lower(), f"Extension should be lowercase: {ext}"
    
    def test_common_dangerous_extensions_present(self):
        """Common dangerous extensions are in the list."""
        dangerous = {".exe", ".vbs", ".bat", ".ps1", ".scr", ".docm"}
        
        for ext in dangerous:
            assert ext in SUSPICIOUS_EXTENSIONS, f"Missing: {ext}"
    
    def test_safe_mime_types_common(self):
        """Common safe MIME types are in the list."""
        common_safe = {"application/pdf", "image/jpeg", "image/png", "text/plain"}
        
        for mime in common_safe:
            assert mime in SAFE_MIME_TYPES, f"Missing: {mime}"
