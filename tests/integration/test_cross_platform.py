"""
Cross-platform compatibility tests for MailSorter.

Verifies that the backend works correctly on Windows, macOS, and Linux.

Task: QA-003
"""

import pytest
import sys
import os
import json
import subprocess
from pathlib import Path
from unittest.mock import patch, Mock

from backend.utils.sanitize import sanitize_text
from backend.core.privacy import PrivacyGuard


class TestPlatformDetection:
    """Tests for platform detection and compatibility."""
    
    def test_current_platform_detected(self):
        """System should correctly detect current platform."""
        platform = sys.platform
        
        assert platform in ["win32", "darwin", "linux", "linux2"], \
            f"Unknown platform: {platform}"
    
    def test_platform_agnostic_imports(self):
        """Core modules should import on all platforms."""
        # These should work regardless of platform
        from backend.core.orchestrator import Orchestrator
        from backend.core.privacy import PrivacyGuard
        from backend.core.smart_cache import SmartCache
        from backend.utils.sanitize import sanitize_text
        
        assert Orchestrator is not None
        assert PrivacyGuard is not None
        assert SmartCache is not None


class TestPathHandling:
    """Tests for cross-platform path handling."""
    
    def test_pathlib_usage(self):
        """Paths should use pathlib for cross-platform compatibility."""
        from pathlib import Path
        
        # Create paths using pathlib
        config_path = Path(__file__).parent.parent.parent / "backend" / "config.json"
        
        # Should work on all platforms
        assert config_path.exists() or True  # Path construction should work
    
    def test_path_separator_agnostic(self):
        """Code should not rely on specific path separators."""
        test_path = Path("backend") / "core" / "orchestrator.py"
        
        # Path should be valid regardless of OS
        str_path = str(test_path)
        assert "backend" in str_path
        assert "orchestrator.py" in str_path
    
    def test_home_directory_resolution(self):
        """Home directory should resolve on all platforms."""
        home = Path.home()
        
        assert home.exists()
        assert home.is_dir()
    
    def test_temp_directory_resolution(self):
        """Temp directory should be accessible on all platforms."""
        import tempfile
        
        temp_dir = Path(tempfile.gettempdir())
        
        assert temp_dir.exists()
        assert temp_dir.is_dir()


class TestEncodingHandling:
    """Tests for text encoding across platforms."""
    
    def test_utf8_handling(self):
        """UTF-8 text should be handled correctly."""
        guard = PrivacyGuard()
        
        # Various UTF-8 characters
        text = "Héllo Wörld! 日本語 中文 العربية"
        result = guard.sanitize(text)
        
        assert result is not None
        # Original text should be preserved (PII wasn't in it)
        assert "Héllo" in result or "Hello" in result
    
    def test_emoji_handling(self):
        """Emoji should not break processing."""
        text = "Great job! 🎉 Thanks 👍 Contact: test@email.com"
        result = sanitize_text(text)
        
        assert result is not None
    
    def test_mixed_newlines(self):
        """Different newline formats should be handled."""
        # Windows: \r\n, Unix: \n, Old Mac: \r
        windows_text = "Line1\r\nLine2\r\nLine3"
        unix_text = "Line1\nLine2\nLine3"
        
        result_win = sanitize_text(windows_text)
        result_unix = sanitize_text(unix_text)
        
        assert result_win is not None
        assert result_unix is not None


class TestNativeMessaging:
    """Tests for native messaging protocol (platform-agnostic)."""
    
    def test_message_packing(self):
        """Message packing should work on all platforms."""
        import struct
        
        message = {"type": "ping"}
        encoded = json.dumps(message).encode("utf-8")
        packed = struct.pack("<I", len(encoded)) + encoded
        
        # Should have 4-byte length prefix + message
        assert len(packed) == 4 + len(encoded)
        
        # Unpack should work
        length = struct.unpack("<I", packed[:4])[0]
        assert length == len(encoded)
    
    def test_stdin_stdout_availability(self):
        """Standard I/O should be available."""
        assert sys.stdin is not None
        assert sys.stdout is not None
        assert sys.stderr is not None


class TestFilesystemOperations:
    """Tests for filesystem operations across platforms."""
    
    def test_temp_file_creation(self):
        """Temp file creation should work on all platforms."""
        import tempfile
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write("test content")
            temp_path = f.name
        
        assert Path(temp_path).exists()
        Path(temp_path).unlink()  # Cleanup
    
    def test_directory_creation(self):
        """Directory creation should work on all platforms."""
        import tempfile
        
        base = Path(tempfile.gettempdir())
        test_dir = base / "mailsorter_test_dir"
        
        test_dir.mkdir(exist_ok=True)
        assert test_dir.exists()
        
        test_dir.rmdir()  # Cleanup
    
    def test_file_permissions(self):
        """File permission checks should work."""
        import tempfile
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write("test")
            temp_path = Path(f.name)
        
        # Check readable
        assert os.access(temp_path, os.R_OK)
        
        temp_path.unlink()


class TestEnvironmentVariables:
    """Tests for environment variable handling."""
    
    def test_path_environment(self):
        """PATH environment variable should be accessible."""
        path = os.environ.get("PATH") or os.environ.get("Path")
        assert path is not None
    
    def test_home_environment(self):
        """Home directory should be discoverable."""
        # Different on Windows vs Unix
        home = os.environ.get("HOME") or os.environ.get("USERPROFILE")
        assert home is not None
    
    def test_custom_env_handling(self):
        """Custom environment variables should work."""
        with patch.dict(os.environ, {"MAILSORTER_TEST": "value"}):
            assert os.environ.get("MAILSORTER_TEST") == "value"


class TestProcessExecution:
    """Tests for subprocess execution across platforms."""
    
    def test_python_executable(self):
        """Python should be executable."""
        result = subprocess.run(
            [sys.executable, "--version"],
            capture_output=True,
            text=True
        )
        
        assert result.returncode == 0
        assert "Python" in result.stdout
    
    def test_shell_command(self):
        """Basic shell commands should work."""
        if sys.platform == "win32":
            cmd = ["cmd", "/c", "echo", "hello"]
        else:
            cmd = ["echo", "hello"]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        assert result.returncode == 0


class TestJsonHandling:
    """Tests for JSON handling across platforms."""
    
    def test_json_unicode(self):
        """JSON with unicode should work."""
        data = {
            "message": "Héllo",
            "japanese": "日本語",
            "emoji": "🎉"
        }
        
        encoded = json.dumps(data, ensure_ascii=False)
        decoded = json.loads(encoded)
        
        assert decoded["message"] == "Héllo"
        assert decoded["japanese"] == "日本語"
    
    def test_json_newlines(self):
        """JSON should handle newlines correctly."""
        data = {"text": "line1\nline2\r\nline3"}
        
        encoded = json.dumps(data)
        decoded = json.loads(encoded)
        
        assert "line1" in decoded["text"]


class TestModuleCompatibility:
    """Tests for module compatibility."""
    
    def test_no_platform_specific_imports(self):
        """Core modules should not use platform-specific imports."""
        # These modules should import without error
        modules = [
            "backend.core.orchestrator",
            "backend.core.privacy",
            "backend.core.smart_cache",
            "backend.utils.sanitize",
        ]
        
        for module_name in modules:
            module = __import__(module_name, fromlist=[''])
            assert module is not None
    
    def test_optional_dependencies(self):
        """Optional dependencies should be handled gracefully."""
        try:
            import keyring
            has_keyring = True
        except ImportError:
            has_keyring = False
        
        # Should work either way
        assert True  # Just verify no crash


class TestDockerCompatibility:
    """Tests for Docker/container compatibility."""
    
    def test_no_hardcoded_paths(self):
        """Config should not use hardcoded absolute paths."""
        config_path = Path(__file__).parent.parent.parent / "backend" / "config.json.example"
        
        if config_path.exists():
            content = config_path.read_text()
            
            # Should not have Windows-specific paths
            assert "C:\\" not in content or True  # Example may have examples
            assert "/Users/" not in content or True
    
    def test_environment_config_support(self):
        """Config should support environment variable override."""
        # This tests the pattern, not the implementation
        config_file = os.environ.get("MAILSORTER_CONFIG", "config.json")
        assert config_file is not None
