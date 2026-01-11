"""
Attachment heuristic analysis for MailSorter.

Provides lightweight security scoring based on attachment metadata
without analyzing attachment content (RGPD compliance).

Scoring adjustments:
- Suspicious: +0.3 phishing score
- Safe indicators: -0.2 phishing score
"""

import hashlib
import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# Suspicious file extensions (high risk)
SUSPICIOUS_EXTENSIONS = {
    # Executables
    ".exe",
    ".scr",
    ".bat",
    ".cmd",
    ".com",
    ".pif",
    ".msi",
    ".msp",
    # Scripts
    ".vbs",
    ".vbe",
    ".js",
    ".jse",
    ".ws",
    ".wsf",
    ".wsc",
    ".wsh",
    ".ps1",
    ".psm1",
    ".psd1",
    # Office macros
    ".docm",
    ".xlsm",
    ".pptm",
    ".dotm",
    ".xltm",
    ".potm",
    # Archives that can contain executables
    ".iso",
    ".img",
    # Double extensions often used in attacks
    ".pdf.exe",
    ".doc.exe",
    ".jpg.exe",
}

# Suspicious MIME types
SUSPICIOUS_MIME_TYPES = {
    "application/x-msdownload",
    "application/x-msdos-program",
    "application/x-executable",
    "application/x-dosexec",
    "application/vnd.ms-excel.sheet.macroEnabled.12",
    "application/vnd.ms-word.document.macroEnabled.12",
    "application/vnd.ms-powerpoint.presentation.macroEnabled.12",
    "application/x-javascript",
    "text/javascript",
    "application/hta",
}

# Safe/common attachment types (reduce suspicion)
SAFE_MIME_TYPES = {
    "application/pdf",
    "image/jpeg",
    "image/png",
    "image/gif",
    "text/plain",
    "text/csv",
}

# Known malware hashes (sample - in production, use threat intelligence feed)
KNOWN_MALWARE_HASHES: set[str] = set()  # Populated from threat feed


class AttachmentHeuristic:
    """
    Analyze attachment metadata for security indicators.

    Does NOT read attachment content (RGPD compliance).
    Only analyzes: filename, MIME type, size, and optionally hash.
    """

    def __init__(self):
        self.suspicious_extensions = SUSPICIOUS_EXTENSIONS
        self.suspicious_mime_types = SUSPICIOUS_MIME_TYPES
        self.safe_mime_types = SAFE_MIME_TYPES

    def analyze_attachment(
        self,
        filename: str,
        mime_type: str,
        size_bytes: int = 0,
        content_hash: Optional[str] = None,
    ) -> Dict:
        """
        Analyze a single attachment.

        Args:
            filename: Attachment filename
            mime_type: MIME type string
            size_bytes: File size in bytes
            content_hash: Optional SHA256 hash of content

        Returns:
            Analysis result with score adjustment and flags
        """
        score_adjustment: float = 0.0
        flags: List[str] = []
        risk_level = "low"

        # Check for suspicious extension
        ext_lower = self._get_extension(filename).lower()
        if ext_lower in self.suspicious_extensions:
            score_adjustment += 0.3
            flags.append(f"suspicious_extension:{ext_lower}")
            risk_level = "high"

        # Check for double extension (e.g., document.pdf.exe)
        if self._has_double_extension(filename):
            score_adjustment += 0.4
            flags.append("double_extension")
            risk_level = "high"

        # Check MIME type
        mime_lower = mime_type.lower() if mime_type else ""
        if mime_lower in self.suspicious_mime_types:
            score_adjustment += 0.25
            flags.append(f"suspicious_mime:{mime_lower}")
            if risk_level != "high":
                risk_level = "medium"
        elif mime_lower in self.safe_mime_types:
            score_adjustment -= 0.1
            flags.append("safe_mime_type")

        # Check for MIME/extension mismatch
        if self._has_mime_mismatch(filename, mime_type):
            score_adjustment += 0.2
            flags.append("mime_extension_mismatch")
            if risk_level == "low":
                risk_level = "medium"

        # Check known malware hash
        if content_hash and content_hash.lower() in KNOWN_MALWARE_HASHES:
            score_adjustment += 0.9
            flags.append("known_malware_hash")
            risk_level = "critical"

        # Suspicious size (very small executables or very large files)
        if ext_lower in {".exe", ".msi"} and size_bytes > 0 and size_bytes < 10000:
            score_adjustment += 0.15
            flags.append("suspiciously_small_executable")

        # Clamp adjustment
        score_adjustment = max(-0.5, min(0.9, score_adjustment))

        return {
            "filename": filename,
            "mime_type": mime_type,
            "size_bytes": size_bytes,
            "score_adjustment": score_adjustment,
            "flags": flags,
            "risk_level": risk_level,
        }

    def analyze_attachments(self, attachments: List[Dict]) -> Dict:
        """
        Analyze multiple attachments.

        Args:
            attachments: List of dicts with filename, mime_type, size_bytes

        Returns:
            Aggregate analysis result
        """
        if not attachments:
            return {
                "total_attachments": 0,
                "aggregate_score_adjustment": 0.0,
                "highest_risk": "none",
                "details": [],
            }

        details = []
        highest_risk = "low"
        risk_order = {"none": 0, "low": 1, "medium": 2, "high": 3, "critical": 4}

        for att in attachments:
            analysis = self.analyze_attachment(
                filename=att.get("filename", "unknown"),
                mime_type=att.get("mime_type", ""),
                size_bytes=att.get("size_bytes", 0),
                content_hash=att.get("hash"),
            )
            details.append(analysis)

            if risk_order.get(analysis["risk_level"], 0) > risk_order.get(
                highest_risk, 0
            ):
                highest_risk = analysis["risk_level"]

        # Aggregate score: take the highest adjustment (not sum, to avoid over-penalizing)
        adjustments = [d["score_adjustment"] for d in details]
        aggregate = max(adjustments) if adjustments else 0.0

        # Bonus penalty for multiple suspicious attachments
        high_risk_count = sum(
            1 for d in details if d["risk_level"] in ("high", "critical")
        )
        if high_risk_count > 1:
            aggregate = min(0.9, aggregate + 0.1 * (high_risk_count - 1))

        return {
            "total_attachments": len(attachments),
            "aggregate_score_adjustment": round(aggregate, 3),
            "highest_risk": highest_risk,
            "details": details,
        }

    def _get_extension(self, filename: str) -> str:
        """Extract file extension."""
        if not filename:
            return ""
        parts = filename.rsplit(".", 1)
        return f".{parts[-1]}" if len(parts) > 1 else ""

    def _has_double_extension(self, filename: str) -> bool:
        """Check for suspicious double extension."""
        if not filename:
            return False

        # Patterns like: file.pdf.exe, document.doc.scr
        parts = filename.lower().split(".")
        if len(parts) < 3:
            return False

        last_ext = f".{parts[-1]}"
        second_last = f".{parts[-2]}"

        # Check if last is executable and second-last is document
        doc_extensions = {
            ".pdf",
            ".doc",
            ".docx",
            ".xls",
            ".xlsx",
            ".jpg",
            ".png",
            ".txt",
        }
        exec_extensions = {
            ".exe",
            ".scr",
            ".bat",
            ".cmd",
            ".com",
            ".pif",
            ".vbs",
            ".js",
        }

        return last_ext in exec_extensions and second_last in doc_extensions

    def _has_mime_mismatch(self, filename: str, mime_type: str) -> bool:
        """Check if MIME type doesn't match extension."""
        if not filename or not mime_type:
            return False

        ext = self._get_extension(filename).lower()
        mime = mime_type.lower()

        # Known safe combinations
        valid_combos = {
            ".pdf": {"application/pdf"},
            ".jpg": {"image/jpeg"},
            ".jpeg": {"image/jpeg"},
            ".png": {"image/png"},
            ".gif": {"image/gif"},
            ".txt": {"text/plain"},
            ".html": {"text/html"},
            ".csv": {"text/csv", "text/plain"},
            ".json": {"application/json", "text/plain"},
            ".xml": {"application/xml", "text/xml"},
        }

        if ext in valid_combos:
            return mime not in valid_combos[ext]

        return False


def compute_file_hash(content: bytes) -> str:
    """
    Compute SHA256 hash of file content.

    Args:
        content: File content as bytes

    Returns:
        Hex-encoded SHA256 hash
    """
    return hashlib.sha256(content).hexdigest()
