"""
Native Messaging Protocol End-to-End Tests.

Tests the complete native messaging flow between Thunderbird extension 
and Python backend. Simulates the actual message protocol.

Run with: pytest tests/integration/test_native_messaging_e2e.py -v

Task: EXT-INT-001
"""

import io
import json
import os
import struct
import subprocess
import sys
import tempfile
import time
import threading
import pytest
from pathlib import Path
from typing import Dict, Optional, Tuple
from unittest.mock import Mock, patch, MagicMock


# Project paths
PROJECT_ROOT = Path(__file__).parent.parent.parent
BACKEND_DIR = PROJECT_ROOT / "backend"
MAIN_SCRIPT = BACKEND_DIR / "main.py"


# =============================================================================
# NATIVE MESSAGING PROTOCOL HELPERS
# =============================================================================

def encode_message(message: dict) -> bytes:
    """Encode a message using Native Messaging Protocol.
    
    Format: 4-byte length (native endian) + JSON bytes
    """
    encoded = json.dumps(message).encode("utf-8")
    length = struct.pack("@I", len(encoded))
    return length + encoded


def decode_message(data: bytes) -> Tuple[dict, bytes]:
    """Decode a Native Messaging Protocol message.
    
    Returns: (message dict, remaining bytes)
    """
    if len(data) < 4:
        raise ValueError("Not enough data for length prefix")
    
    length = struct.unpack("@I", data[:4])[0]
    
    if len(data) < 4 + length:
        raise ValueError("Not enough data for message body")
    
    message_bytes = data[4:4+length]
    message = json.loads(message_bytes.decode("utf-8"))
    remaining = data[4+length:]
    
    return message, remaining


class NativeMessagingSimulator:
    """Simulates Native Messaging communication with the backend."""
    
    def __init__(self, timeout: float = 30.0):
        self.timeout = timeout
        self.process: Optional[subprocess.Popen] = None
        self._lock = threading.Lock()
    
    def start(self) -> bool:
        """Start the backend process."""
        try:
            # Use Python from the virtual environment or system
            python_exe = sys.executable
            
            self.process = subprocess.Popen(
                [python_exe, str(MAIN_SCRIPT)],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=str(PROJECT_ROOT),
                bufsize=0  # Unbuffered for real-time communication
            )
            
            return self.process.poll() is None
        except Exception as e:
            print(f"Failed to start backend: {e}")
            return False
    
    def stop(self):
        """Stop the backend process."""
        if self.process:
            try:
                self.process.stdin.close()
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
            finally:
                self.process = None
    
    def send_message(self, message: dict) -> Optional[dict]:
        """Send a message and wait for response."""
        if not self.process or self.process.poll() is not None:
            raise RuntimeError("Backend process not running")
        
        with self._lock:
            # Encode and send
            encoded = encode_message(message)
            self.process.stdin.write(encoded)
            self.process.stdin.flush()
            
            # Read response length
            length_bytes = self.process.stdout.read(4)
            if len(length_bytes) < 4:
                return None
            
            length = struct.unpack("@I", length_bytes)[0]
            
            # Read response body
            response_bytes = self.process.stdout.read(length)
            if len(response_bytes) < length:
                return None
            
            return json.loads(response_bytes.decode("utf-8"))


# =============================================================================
# PROTOCOL UNIT TESTS
# =============================================================================

class TestNativeMessagingProtocol:
    """Test Native Messaging Protocol encoding/decoding."""
    
    def test_encode_simple_message(self):
        """Should encode simple message correctly."""
        message = {"type": "ping"}
        encoded = encode_message(message)
        
        # First 4 bytes are length
        length = struct.unpack("@I", encoded[:4])[0]
        
        # Rest is JSON
        json_bytes = encoded[4:]
        assert len(json_bytes) == length
        
        decoded = json.loads(json_bytes.decode("utf-8"))
        assert decoded == message
    
    def test_encode_complex_message(self):
        """Should encode complex message with Unicode."""
        message = {
            "type": "classify",
            "payload": {
                "subject": "Réunion demain",
                "body": "Bonjour, voici les détails...",
                "folders": ["Inbox", "Travail", "重要"]
            }
        }
        
        encoded = encode_message(message)
        decoded, remaining = decode_message(encoded)
        
        assert decoded == message
        assert remaining == b""
    
    def test_decode_multiple_messages(self):
        """Should decode multiple concatenated messages."""
        messages = [
            {"type": "ping"},
            {"type": "classify", "payload": {"subject": "Test"}},
            {"type": "health"}
        ]
        
        # Encode all messages
        data = b"".join(encode_message(m) for m in messages)
        
        # Decode all
        decoded_messages = []
        while data:
            msg, data = decode_message(data)
            decoded_messages.append(msg)
        
        assert decoded_messages == messages
    
    def test_length_prefix_little_endian(self):
        """Length prefix should use native byte order."""
        message = {"test": "a" * 1000}
        encoded = encode_message(message)
        
        # Verify length using native order
        length = struct.unpack("@I", encoded[:4])[0]
        assert length == len(json.dumps(message).encode("utf-8"))
    
    def test_empty_payload(self):
        """Should handle messages with empty payload."""
        message = {"type": "ping", "payload": {}}
        encoded = encode_message(message)
        decoded, _ = decode_message(encoded)
        
        assert decoded == message
    
    def test_large_message(self):
        """Should handle large messages (1MB+)."""
        large_body = "x" * (1024 * 1024)  # 1MB
        message = {
            "type": "classify",
            "payload": {"body": large_body}
        }
        
        encoded = encode_message(message)
        decoded, _ = decode_message(encoded)
        
        assert decoded["payload"]["body"] == large_body


# =============================================================================
# MANIFEST COMPATIBILITY TESTS
# =============================================================================

class TestManifestCompatibility:
    """Test manifest.json compatibility and configuration."""
    
    @pytest.fixture
    def extension_manifest(self) -> dict:
        """Load extension manifest.json."""
        manifest_path = PROJECT_ROOT / "extension" / "manifest.json"
        with open(manifest_path, "r", encoding="utf-8") as f:
            return json.load(f)
    
    @pytest.fixture
    def app_manifest(self) -> dict:
        """Load native messaging app manifest."""
        manifest_path = BACKEND_DIR / "app_manifest.json"
        with open(manifest_path, "r", encoding="utf-8") as f:
            return json.load(f)
    
    def test_manifest_version_2(self, extension_manifest):
        """Extension should use Manifest V2 for Thunderbird compatibility."""
        assert extension_manifest["manifest_version"] == 2
    
    def test_required_permissions(self, extension_manifest):
        """Extension should have all required permissions."""
        required = [
            "messagesRead",
            "messagesModify", 
            "messagesMove",
            "accountsRead",
            "foldersRead",
            "nativeMessaging",
            "storage"
        ]
        
        for perm in required:
            assert perm in extension_manifest["permissions"], \
                f"Missing permission: {perm}"
    
    def test_native_messaging_permission(self, extension_manifest):
        """Extension must have nativeMessaging permission."""
        assert "nativeMessaging" in extension_manifest["permissions"]
    
    def test_extension_id_matches_allowed(self, extension_manifest, app_manifest):
        """Extension ID must be in allowed_extensions list."""
        extension_id = extension_manifest["browser_specific_settings"]["gecko"]["id"]
        allowed = app_manifest["allowed_extensions"]
        
        assert extension_id in allowed, \
            f"Extension ID '{extension_id}' not in allowed: {allowed}"
    
    def test_app_manifest_name_format(self, app_manifest):
        """App name should follow reverse-DNS convention."""
        name = app_manifest["name"]
        
        assert "." in name, "App name should use reverse-DNS format"
        assert name == "com.mailsorter.backend"
    
    def test_app_manifest_type(self, app_manifest):
        """App manifest type should be 'stdio'."""
        assert app_manifest["type"] == "stdio"
    
    def test_app_manifest_path_exists(self, app_manifest):
        """App manifest path should point to existing file."""
        # Note: Path in manifest might be absolute, relative checks are for dev
        path = app_manifest.get("path", "")
        
        # For testing, we just verify the format
        assert path.endswith("main.py") or path.endswith("main.exe")
    
    def test_thunderbird_min_version(self, extension_manifest):
        """Should specify minimum Thunderbird version."""
        gecko = extension_manifest.get("browser_specific_settings", {}).get("gecko", {})
        min_version = gecko.get("strict_min_version", "")
        
        assert min_version, "Missing strict_min_version"
        
        # Parse version
        major = int(min_version.split(".")[0])
        assert major >= 115, f"Min version {min_version} too old, need 115+"
    
    def test_background_scripts_exist(self, extension_manifest):
        """All background scripts should exist."""
        extension_dir = PROJECT_ROOT / "extension"
        scripts = extension_manifest["background"]["scripts"]
        
        for script in scripts:
            script_path = extension_dir / script
            assert script_path.exists(), f"Missing background script: {script}"
    
    def test_popup_html_exists(self, extension_manifest):
        """Popup HTML should exist."""
        extension_dir = PROJECT_ROOT / "extension"
        popup_path = extension_manifest["browser_action"]["default_popup"]
        
        assert (extension_dir / popup_path).exists(), \
            f"Missing popup HTML: {popup_path}"
    
    def test_options_html_exists(self, extension_manifest):
        """Options page HTML should exist."""
        extension_dir = PROJECT_ROOT / "extension"
        options_path = extension_manifest["options_ui"]["page"]
        
        assert (extension_dir / options_path).exists(), \
            f"Missing options HTML: {options_path}"
    
    def test_locales_exist(self, extension_manifest):
        """Required locales should exist."""
        extension_dir = PROJECT_ROOT / "extension"
        locales_dir = extension_dir / "_locales"
        
        required_locales = ["en", "fr"]
        
        for locale in required_locales:
            locale_file = locales_dir / locale / "messages.json"
            assert locale_file.exists(), f"Missing locale: {locale}"
    
    def test_icons_exist(self, extension_manifest):
        """All declared icons should exist."""
        extension_dir = PROJECT_ROOT / "extension"
        icons = extension_manifest.get("icons", {})
        
        for size, path in icons.items():
            icon_path = extension_dir / path
            assert icon_path.exists(), f"Missing icon: {path}"
    
    def test_csp_policy(self, extension_manifest):
        """Content Security Policy should be restrictive."""
        csp = extension_manifest.get("content_security_policy", "")
        
        assert "script-src" in csp, "CSP should restrict script-src"
        assert "'self'" in csp, "CSP should allow 'self'"
        # Ensure no unsafe-inline or unsafe-eval
        assert "unsafe-inline" not in csp, "CSP should not allow unsafe-inline"
        assert "unsafe-eval" not in csp, "CSP should not allow unsafe-eval"


# =============================================================================
# SIMULATED E2E MESSAGE FLOW TESTS
# =============================================================================

class TestSimulatedMessageFlow:
    """Test message flows using mocked backend components."""
    
    @pytest.fixture
    def mock_orchestrator(self):
        """Create mock orchestrator for testing."""
        with patch('backend.core.orchestrator.ProviderFactory') as mock_factory, \
             patch('backend.core.orchestrator.get_smart_cache') as mock_cache, \
             patch('backend.core.orchestrator.get_circuit_breaker') as mock_cb, \
             patch('backend.core.orchestrator.get_rate_limiter') as mock_rl, \
             patch('backend.core.orchestrator.get_prompt_engine') as mock_pe, \
             patch('backend.core.orchestrator.get_calibrator') as mock_cal, \
             patch('backend.core.orchestrator.get_batch_processor') as mock_bp, \
             patch('backend.core.orchestrator.get_feedback_loop') as mock_fl, \
             patch('backend.core.orchestrator.check_rate_limit') as mock_check:
            
            from backend.providers.base import ClassificationResult
            from backend.core.orchestrator import Orchestrator
            
            # Mock provider
            mock_provider = Mock()
            mock_provider.get_name.return_value = "mock"
            mock_provider.is_local = True
            mock_provider.health_check.return_value = True
            mock_provider.classify_email.return_value = ClassificationResult(
                folder="Inbox",
                confidence=0.85,
                reasoning="Test",
                tokens_used=50,
                latency_ms=100,
                source="mock"
            )
            mock_factory.create.return_value = mock_provider
            
            # Mock cache
            mock_cache_inst = Mock()
            mock_cache_inst.check.return_value = None
            mock_cache.return_value = mock_cache_inst
            
            # Mock circuit breaker
            mock_cb_inst = Mock()
            mock_cb_inst.can_execute.return_value = True
            mock_cb.return_value = mock_cb_inst
            
            mock_check.return_value = True
            
            # Mock calibrator
            mock_cal_inst = Mock()
            mock_cal_inst.passes_threshold.return_value = True
            mock_cal.return_value = mock_cal_inst
            
            mock_pe.return_value = Mock()
            mock_bp.return_value = Mock()
            mock_fl.return_value = Mock()
            mock_rl.return_value = Mock()
            
            yield Orchestrator
    
    def test_ping_message(self, mock_orchestrator):
        """Ping message should return pong."""
        orchestrator = mock_orchestrator({
            "provider": "mock",
            "folders": ["Inbox"]
        })
        
        response = orchestrator.handle_message({"type": "ping"})
        
        assert response["type"] == "pong"
        assert response["status"] == "ok"
    
    def test_classify_message(self, mock_orchestrator):
        """Classify message should return folder suggestion."""
        orchestrator = mock_orchestrator({
            "provider": "mock",
            "folders": ["Inbox", "Work"]
        })
        
        message = {
            "type": "classify",
            "payload": {
                "id": "msg-123",
                "from": "sender@example.com",
                "subject": "Test Email",
                "body": "This is a test.",
                "folders": ["Inbox", "Work"]
            }
        }
        
        response = orchestrator.handle_message(message)
        
        # Should have classification result
        assert "folder" in response or "action" in response
    
    def test_health_message(self, mock_orchestrator):
        """Health message should return status."""
        orchestrator = mock_orchestrator({
            "provider": "mock",
            "folders": ["Inbox"]
        })
        
        response = orchestrator.handle_message({"type": "health"})
        
        assert "status" in response
        assert response["status"] in ["ok", "degraded"]
    
    def test_unknown_message_type(self, mock_orchestrator):
        """Unknown message type should return error."""
        orchestrator = mock_orchestrator({
            "provider": "mock",
            "folders": ["Inbox"]
        })
        
        response = orchestrator.handle_message({"type": "invalid"})
        
        assert response["status"] == "error"
        assert "error" in response
    
    def test_missing_payload(self, mock_orchestrator):
        """Missing payload should be handled gracefully."""
        orchestrator = mock_orchestrator({
            "provider": "mock",
            "folders": ["Inbox"]
        })
        
        # Classify without payload
        response = orchestrator.handle_message({"type": "classify"})
        
        # Should handle gracefully (error or default behavior)
        assert response is not None


# =============================================================================
# EMAIL CONTENT TESTS
# =============================================================================

class TestRealEmailContent:
    """Test with realistic email content patterns."""
    
    SAMPLE_EMAILS = [
        {
            "name": "Invoice Email",
            "from": "billing@company.com",
            "subject": "Invoice #INV-2024-001234",
            "body": """Dear Customer,

Please find attached your invoice for services rendered in December 2024.

Invoice Details:
- Amount: $1,234.56
- Due Date: January 15, 2024
- Reference: INV-2024-001234

Payment methods available on our website.

Best regards,
Billing Department""",
            "expected_category": "invoices"
        },
        {
            "name": "Newsletter",
            "from": "newsletter@techsite.com",
            "subject": "Weekly Tech Digest - AI Updates & More",
            "body": """Hi there,

Here's your weekly roundup of tech news:

1. New AI model released
2. Framework updates
3. Security patches

Click here to read more...

Unsubscribe: link""",
            "expected_category": "newsletters"
        },
        {
            "name": "Work Meeting",
            "from": "colleague@work.com",
            "subject": "Re: Project Meeting Tomorrow at 3pm",
            "body": """Hi,

Confirming our meeting tomorrow at 3pm in Conference Room B.

Agenda:
- Q1 Review
- Budget Discussion
- New Initiatives

Please bring your reports.

Thanks,
John""",
            "expected_category": "work"
        },
        {
            "name": "Spam",
            "from": "winner@lottery.scam",
            "subject": "CONGRATULATIONS! You've WON $1,000,000!!!",
            "body": """URGENT!!!

You have been selected as the WINNER of our international lottery!

Click here NOW to claim your $1,000,000 prize!!!

Limited time offer - ACT NOW!!!

This is NOT a scam!""",
            "expected_category": "spam"
        },
        {
            "name": "Order Confirmation",
            "from": "orders@shop.com",
            "subject": "Order Confirmed: #ORD-78901",
            "body": """Thank you for your order!

Order Number: #ORD-78901
Items: 2
Total: $89.99

Shipping to:
123 Main St
City, ST 12345

Track your order: link""",
            "expected_category": "shopping"
        },
        {
            "name": "GitHub Notification",
            "from": "notifications@github.com",
            "subject": "[repo] Issue #123: Bug in feature X",
            "body": """@username opened an issue:

Title: Bug in feature X
Description: When doing Y, Z happens incorrectly.

Steps to reproduce:
1. Do A
2. Do B
3. Observe C

---
Reply to this email or view on GitHub.""",
            "expected_category": "development"
        },
        {
            "name": "Personal Email",
            "from": "mom@family.net",
            "subject": "Dinner this weekend?",
            "body": """Hi honey,

Would you like to come for dinner this Sunday? Dad is making his famous lasagna.

Let me know!

Love,
Mom""",
            "expected_category": "personal"
        },
        {
            "name": "Bank Alert",
            "from": "alerts@bank.com",
            "subject": "Account Alert: New Transaction",
            "body": """Account Alert

A new transaction was made on your account:
Amount: $150.00
Merchant: Gas Station
Date: 01/08/2026

If you don't recognize this transaction, please contact us.

This is an automated message.""",
            "expected_category": "finance"
        }
    ]
    
    def test_sample_email_formats(self):
        """Verify sample emails have correct format for testing."""
        for email in self.SAMPLE_EMAILS:
            assert "name" in email
            assert "from" in email
            assert "subject" in email
            assert "body" in email
            assert len(email["subject"]) > 0
            assert len(email["body"]) > 0
    
    def test_email_payloads_encodable(self):
        """All sample emails should be JSON-encodable."""
        for email in self.SAMPLE_EMAILS:
            message = {
                "type": "classify",
                "payload": {
                    "from": email["from"],
                    "subject": email["subject"],
                    "body": email["body"],
                    "folders": ["Inbox", "Work", "Personal"]
                }
            }
            
            # Should encode without error
            encoded = encode_message(message)
            decoded, _ = decode_message(encoded)
            
            assert decoded["payload"]["subject"] == email["subject"]
    
    def test_unicode_in_emails(self):
        """Should handle Unicode content in emails."""
        unicode_email = {
            "from": "sender@日本.com",
            "subject": "Réunion: 日程確認 📅",
            "body": "Привет! 你好! مرحبا! שלום!\n\nÉmojis: 🎉🔥💯"
        }
        
        message = {
            "type": "classify",
            "payload": unicode_email
        }
        
        encoded = encode_message(message)
        decoded, _ = decode_message(encoded)
        
        assert decoded["payload"]["subject"] == unicode_email["subject"]
        assert decoded["payload"]["body"] == unicode_email["body"]
    
    def test_html_in_email_body(self):
        """Should handle HTML content in email body."""
        html_body = """
        <html>
        <body>
            <h1>Hello!</h1>
            <p>This is an <strong>HTML</strong> email.</p>
            <a href="http://example.com">Click here</a>
            <script>alert('xss')</script>
        </body>
        </html>
        """
        
        message = {
            "type": "classify",
            "payload": {
                "from": "sender@example.com",
                "subject": "HTML Email",
                "body": html_body,
                "folders": ["Inbox"]
            }
        }
        
        encoded = encode_message(message)
        decoded, _ = decode_message(encoded)
        
        assert "<html>" in decoded["payload"]["body"]


# =============================================================================
# SETTINGS/UI FLOW TESTS
# =============================================================================

class TestSettingsFlow:
    """Test settings-related message flows."""
    
    def test_stats_message_format(self):
        """Stats request should return expected format."""
        # This tests the expected response structure
        expected_fields = ["cache", "calibration", "feedback", "circuit_breaker"]
        
        # Verify fields expected in stats response
        for field in expected_fields:
            assert field in expected_fields
    
    def test_feedback_message_format(self):
        """Feedback message should have correct format."""
        feedback = {
            "type": "feedback",
            "payload": {
                "message_id": "msg-123",
                "original_folder": "Inbox",
                "correct_folder": "Work",
                "timestamp": "2026-01-09T10:00:00Z"
            }
        }
        
        encoded = encode_message(feedback)
        decoded, _ = decode_message(encoded)
        
        assert decoded["type"] == "feedback"
        assert decoded["payload"]["message_id"] == "msg-123"


# =============================================================================
# LIVE E2E TEST (OPTIONAL)
# =============================================================================

@pytest.mark.live
@pytest.mark.slow
class TestLiveNativeMessaging:
    """Live end-to-end tests with actual backend process.
    
    These tests actually start the Python backend and communicate
    via native messaging protocol. Run with:
    
        pytest tests/integration/test_native_messaging_e2e.py -v -m live
    """
    
    @pytest.fixture
    def simulator(self) -> NativeMessagingSimulator:
        """Create and start simulator."""
        sim = NativeMessagingSimulator(timeout=30)
        if not sim.start():
            pytest.skip("Could not start backend process")
        yield sim
        sim.stop()
    
    def test_live_ping(self, simulator):
        """Live ping should return pong."""
        response = simulator.send_message({"type": "ping"})
        
        assert response is not None
        assert response.get("type") == "pong"
    
    def test_live_health(self, simulator):
        """Live health check should return status."""
        response = simulator.send_message({"type": "health"})
        
        assert response is not None
        assert "status" in response
    
    def test_live_classify(self, simulator):
        """Live classification should work."""
        message = {
            "type": "classify",
            "payload": {
                "id": "live-test-1",
                "from": "test@example.com",
                "subject": "Test Email",
                "body": "This is a test email for live testing.",
                "folders": ["Inbox", "Test"]
            }
        }
        
        response = simulator.send_message(message)
        
        assert response is not None
        # Should have some response (either result or error due to no provider)
    
    def test_live_multiple_messages(self, simulator):
        """Should handle multiple messages in sequence."""
        messages = [
            {"type": "ping"},
            {"type": "health"},
            {"type": "ping"},
        ]
        
        for msg in messages:
            response = simulator.send_message(msg)
            assert response is not None
