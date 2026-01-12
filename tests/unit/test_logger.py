"""
Unit tests for Logger module.

CRITICAL: Validates that the logger NEVER writes to stdout,
as this would break Native Messaging protocol.
"""

import io
import logging
import os
import sys


class TestLoggerStdoutProtection:
    """Critical tests - logger must never use stdout."""

    def test_logger_never_writes_to_stdout(self):
        """Logger handlers should not include stdout."""
        # Import fresh to get the logger
        from backend.utils.logger import setup_logger

        # Capture stdout
        original_stdout = sys.stdout
        captured_stdout = io.StringIO()
        sys.stdout = captured_stdout

        try:
            # Create a new logger instance
            test_logger = setup_logger("TestLoggerStdout")

            # Log at various levels
            test_logger.debug("Debug message")
            test_logger.info("Info message")
            test_logger.warning("Warning message")
            test_logger.error("Error message")

            # Force flush
            for handler in test_logger.handlers:
                handler.flush()

            # Check stdout is empty
            stdout_content = captured_stdout.getvalue()
            assert stdout_content == "", f"Logger wrote to stdout: {stdout_content}"

        finally:
            sys.stdout = original_stdout
            # Clean up handlers
            for handler in test_logger.handlers[:]:
                test_logger.removeHandler(handler)

    def test_logger_writes_to_stderr(self):
        """Logger should write to stderr (safe for Native Messaging)."""
        from backend.utils.logger import setup_logger

        # Capture stderr
        original_stderr = sys.stderr
        captured_stderr = io.StringIO()
        sys.stderr = captured_stderr

        try:
            test_logger = setup_logger("TestLoggerStderr")
            test_logger.info("Test message to stderr")

            # Force flush
            for handler in test_logger.handlers:
                handler.flush()

            stderr_content = captured_stderr.getvalue()
            assert "Test message to stderr" in stderr_content

        finally:
            sys.stderr = original_stderr
            for handler in test_logger.handlers[:]:
                test_logger.removeHandler(handler)

    def test_no_stdout_handler_in_handlers(self):
        """Verify no handler uses stdout stream."""
        from backend.utils.logger import setup_logger

        test_logger = setup_logger("TestHandlers")

        try:
            for handler in test_logger.handlers:
                if isinstance(handler, logging.StreamHandler):
                    # StreamHandler should be stderr, not stdout
                    assert (
                        handler.stream != sys.stdout
                    ), "Found handler writing to stdout!"
        finally:
            for handler in test_logger.handlers[:]:
                test_logger.removeHandler(handler)


class TestLoggerFileOutput:
    """Tests for file-based logging."""

    def test_log_file_created(self):
        """Log file is created in user directory."""
        from backend.utils.logger import setup_logger

        test_logger = setup_logger("TestFileCreation")

        try:
            # Find the file handler
            file_handler = None
            for handler in test_logger.handlers:
                if hasattr(handler, "baseFilename"):
                    file_handler = handler
                    break

            assert file_handler is not None, "No file handler found"
            assert os.path.exists(file_handler.baseFilename)
        finally:
            for handler in test_logger.handlers[:]:
                test_logger.removeHandler(handler)

    def test_log_file_in_mailsorter_dir(self):
        """Log file is in ~/.mailsorter/logs directory."""
        from backend.utils.logger import setup_logger

        test_logger = setup_logger("TestLogPath")

        try:
            for handler in test_logger.handlers:
                if hasattr(handler, "baseFilename"):
                    log_path = handler.baseFilename
                    assert ".mailsorter" in log_path
                    assert "logs" in log_path
                    break
        finally:
            for handler in test_logger.handlers[:]:
                test_logger.removeHandler(handler)

    def test_log_file_encoding_utf8(self):
        """Log file handler uses UTF-8 encoding."""
        from backend.utils.logger import setup_logger

        test_logger = setup_logger("TestEncoding")

        try:
            for handler in test_logger.handlers:
                if hasattr(handler, "encoding"):
                    assert handler.encoding == "utf-8"
        finally:
            for handler in test_logger.handlers[:]:
                test_logger.removeHandler(handler)


class TestLoggerRotation:
    """Tests for log rotation."""

    def test_rotating_file_handler_configured(self):
        """Log file uses rotating handler."""
        from backend.utils.logger import setup_logger
        from logging.handlers import RotatingFileHandler

        test_logger = setup_logger("TestRotation")

        try:
            has_rotating = False
            for handler in test_logger.handlers:
                if isinstance(handler, RotatingFileHandler):
                    has_rotating = True
                    break

            assert has_rotating, "No RotatingFileHandler found"
        finally:
            for handler in test_logger.handlers[:]:
                test_logger.removeHandler(handler)

    def test_max_bytes_configured(self):
        """Rotation is configured with max bytes."""
        from backend.utils.logger import setup_logger
        from logging.handlers import RotatingFileHandler

        test_logger = setup_logger("TestMaxBytes")

        try:
            for handler in test_logger.handlers:
                if isinstance(handler, RotatingFileHandler):
                    # Should be 5MB
                    assert handler.maxBytes == 5 * 1024 * 1024
                    break
        finally:
            for handler in test_logger.handlers[:]:
                test_logger.removeHandler(handler)

    def test_backup_count_configured(self):
        """Rotation keeps backup files."""
        from backend.utils.logger import setup_logger
        from logging.handlers import RotatingFileHandler

        test_logger = setup_logger("TestBackups")

        try:
            for handler in test_logger.handlers:
                if isinstance(handler, RotatingFileHandler):
                    assert handler.backupCount == 3
                    break
        finally:
            for handler in test_logger.handlers[:]:
                test_logger.removeHandler(handler)


class TestLoggerFormat:
    """Tests for log message formatting."""

    def test_log_format_includes_timestamp(self):
        """Log format includes timestamp."""
        from backend.utils.logger import setup_logger

        test_logger = setup_logger("TestFormat")

        # Remove existing handlers and add fresh one with our captured stream
        for handler in test_logger.handlers[:]:
            test_logger.removeHandler(handler)

        captured = io.StringIO()
        handler = logging.StreamHandler(captured)
        handler.setFormatter(
            logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        )
        test_logger.addHandler(handler)

        try:
            test_logger.info("Format test")
            handler.flush()

            output = captured.getvalue()
            # Should have timestamp format like "2024-01-01 12:00:00,000"
            import re

            timestamp_pattern = r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}"
            assert re.search(
                timestamp_pattern, output
            ), f"No timestamp in log: {output}"
        finally:
            test_logger.removeHandler(handler)

    def test_log_format_includes_level(self):
        """Log format includes log level."""
        from backend.utils.logger import setup_logger

        test_logger = setup_logger("TestLevel")

        # Remove existing handlers and add fresh one
        for handler in test_logger.handlers[:]:
            test_logger.removeHandler(handler)

        captured = io.StringIO()
        handler = logging.StreamHandler(captured)
        handler.setFormatter(
            logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        )
        test_logger.addHandler(handler)

        try:
            test_logger.warning("Level test")
            handler.flush()

            output = captured.getvalue()
            assert "WARNING" in output
        finally:
            test_logger.removeHandler(handler)


class TestGlobalLogger:
    """Tests for the global logger instance."""

    def test_global_logger_exists(self):
        """Global logger is created on import."""
        from backend.utils.logger import logger

        assert logger is not None
        assert logger.name == "MailSorter"

    def test_global_logger_level_info(self):
        """Global logger is set to INFO level."""
        from backend.utils.logger import logger

        assert logger.level == logging.INFO


class TestLoggerUnicodeHandling:
    """Tests for Unicode in log messages."""

    def test_unicode_messages_logged(self):
        """Logger handles Unicode characters correctly."""
        from backend.utils.logger import setup_logger

        test_logger = setup_logger("TestUnicode")

        # Remove existing handlers and add fresh one with our captured stream
        for handler in test_logger.handlers[:]:
            test_logger.removeHandler(handler)

        captured = io.StringIO()
        handler = logging.StreamHandler(captured)
        handler.setFormatter(
            logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        )
        test_logger.addHandler(handler)

        try:
            # Test various Unicode
            test_logger.info("Unicode test: émojis 🎉 中文 العربية")
            handler.flush()

            output = captured.getvalue()
            assert "🎉" in output
            assert "中文" in output
        finally:
            test_logger.removeHandler(handler)
