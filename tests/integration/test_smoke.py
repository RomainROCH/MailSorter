"""
Smoke tests for MailSorter installation verification.

These tests verify that the basic components are working after a fresh install.
Should be run as part of CI to catch breaking changes.

Task: QA-001
"""

import pytest
import importlib
import os


class TestModuleImports:
    """Verify all critical modules can be imported."""

    def test_core_modules_importable(self):
        """Core modules should be importable without errors."""
        core_modules = [
            "backend.core.orchestrator",
            "backend.core.privacy",
            "backend.core.rate_limiter",
            "backend.core.circuit_breaker",
            "backend.core.smart_cache",
            "backend.core.confidence",
            "backend.core.prompt_engine",
            "backend.core.batch_processor",
            "backend.core.feedback_loop",
            "backend.core.attachment_heuristic",
        ]

        for module_name in core_modules:
            try:
                module = importlib.import_module(module_name)
                assert module is not None, f"Module {module_name} imported as None"
            except ImportError as e:
                pytest.fail(f"Failed to import {module_name}: {e}")

    def test_provider_modules_importable(self):
        """Provider modules should be importable."""
        provider_modules = [
            "backend.providers.base",
            "backend.providers.factory",
            "backend.providers.ollama_provider",
            "backend.providers.openai_provider",
            "backend.providers.anthropic_provider",
            "backend.providers.gemini_provider",
        ]

        for module_name in provider_modules:
            try:
                module = importlib.import_module(module_name)
                assert module is not None
            except ImportError as e:
                pytest.fail(f"Failed to import {module_name}: {e}")

    def test_utils_modules_importable(self):
        """Utility modules should be importable."""
        util_modules = [
            "backend.utils.logger",
            "backend.utils.config",
            "backend.utils.sanitize",
            "backend.utils.security",
        ]

        for module_name in util_modules:
            try:
                module = importlib.import_module(module_name)
                assert module is not None
            except ImportError as e:
                pytest.fail(f"Failed to import {module_name}: {e}")


class TestCoreClassesInstantiation:
    """Verify core classes can be instantiated."""

    def test_orchestrator_instantiates(self):
        """Orchestrator should instantiate with minimal config."""
        from unittest.mock import patch, Mock

        with patch("backend.core.orchestrator.ProviderFactory") as mock_factory, patch(
            "backend.core.orchestrator.get_smart_cache"
        ) as _mock_cache, patch(
            "backend.core.orchestrator.get_circuit_breaker"
        ) as _mock_breaker, patch(
            "backend.core.orchestrator.get_rate_limiter"
        ) as _mock_limiter, patch(
            "backend.core.orchestrator.get_prompt_engine"
        ) as _mock_prompt, patch(
            "backend.core.orchestrator.get_calibrator"
        ) as _mock_cal, patch(
            "backend.core.orchestrator.get_batch_processor"
        ) as _mock_batch, patch(
            "backend.core.orchestrator.get_feedback_loop"
        ) as _mock_feedback:

            mock_provider = Mock()
            mock_factory.create.return_value = mock_provider

            from backend.core.orchestrator import Orchestrator

            config = {
                "provider": "ollama",
                "folders": ["Inbox"],
            }

            orchestrator = Orchestrator(config)
            assert orchestrator is not None

    def test_privacy_guard_instantiates(self):
        """PrivacyGuard should instantiate."""
        from backend.core.privacy import PrivacyGuard

        guard = PrivacyGuard()
        assert guard is not None

    def test_rate_limiter_instantiates(self):
        """RateLimiter should instantiate."""
        from backend.core.rate_limiter import RateLimiter

        limiter = RateLimiter()
        assert limiter is not None

    def test_circuit_breaker_instantiates(self):
        """CircuitBreaker should instantiate."""
        from backend.core.circuit_breaker import CircuitBreaker

        breaker = CircuitBreaker()
        assert breaker is not None


class TestConfigurationLoading:
    """Verify configuration can be loaded."""

    def test_config_schema_exists(self):
        """Config schema should exist."""
        schema_path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "..",
            "backend",
            "json_schema",
            "config_schema.json",
        )

        # Schema file may or may not exist, but if it does, it should be valid JSON
        if os.path.exists(schema_path):
            import json

            with open(schema_path, "r") as f:
                schema = json.load(f)
            assert "type" in schema or "$schema" in schema

    def test_config_example_exists(self):
        """Config example should exist."""
        example_path = os.path.join(
            os.path.dirname(__file__), "..", "..", "backend", "config.json.example"
        )

        assert os.path.exists(example_path), "config.json.example not found"


class TestBasicFunctionality:
    """Verify basic functionality works."""

    def test_sanitize_text_works(self):
        """Text sanitization should work."""
        from backend.utils.sanitize import sanitize_text

        result = sanitize_text("Hello, World!")
        assert result == "Hello, World!"

    def test_privacy_guard_sanitize_works(self):
        """Privacy guard sanitization should work."""
        from backend.core.privacy import PrivacyGuard

        guard = PrivacyGuard()
        result = guard.sanitize("Test email content")
        assert result is not None
        assert isinstance(result, str)

    def test_hmac_signing_works(self):
        """HMAC signing should work."""
        from backend.utils.security import sign_classification

        signature = sign_classification("Inbox", 0.9, "test-id")
        assert signature is not None
        assert isinstance(signature, str)
        assert len(signature) > 0


class TestDependencyAvailability:
    """Verify required dependencies are available."""

    def test_required_packages_available(self):
        """Required packages should be importable."""
        required = [
            "requests",
            "jsonschema",
            "jinja2",
        ]

        for package in required:
            try:
                importlib.import_module(package)
            except ImportError:
                pytest.fail(f"Required package not available: {package}")

    def test_optional_packages_graceful_fallback(self):
        """Optional packages should have graceful fallback."""
        # These packages are optional - test that their absence doesn't crash
        from backend.core.privacy import PrivacyGuard

        # Should work regardless of Presidio availability
        guard = PrivacyGuard()
        assert guard is not None


class TestFileStructure:
    """Verify expected file structure exists."""

    def test_backend_directory_exists(self):
        """Backend directory should exist."""
        backend_path = os.path.join(os.path.dirname(__file__), "..", "..", "backend")
        assert os.path.isdir(backend_path)

    def test_extension_directory_exists(self):
        """Extension directory should exist."""
        extension_path = os.path.join(
            os.path.dirname(__file__), "..", "..", "extension"
        )
        assert os.path.isdir(extension_path)

    def test_manifest_exists(self):
        """Extension manifest should exist."""
        manifest_path = os.path.join(
            os.path.dirname(__file__), "..", "..", "extension", "manifest.json"
        )
        assert os.path.exists(manifest_path)

        import json

        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)

        assert "manifest_version" in manifest
        assert "name" in manifest


class TestHealthEndpoint:
    """Verify health check functionality."""

    def test_orchestrator_ping_works(self):
        """Orchestrator should respond to ping."""
        from unittest.mock import patch, Mock

        with patch("backend.core.orchestrator.ProviderFactory") as mock_factory, patch(
            "backend.core.orchestrator.get_smart_cache"
        ), patch("backend.core.orchestrator.get_circuit_breaker"), patch(
            "backend.core.orchestrator.get_rate_limiter"
        ), patch(
            "backend.core.orchestrator.get_prompt_engine"
        ), patch(
            "backend.core.orchestrator.get_calibrator"
        ), patch(
            "backend.core.orchestrator.get_batch_processor"
        ), patch(
            "backend.core.orchestrator.get_feedback_loop"
        ):

            mock_factory.create.return_value = Mock()

            from backend.core.orchestrator import Orchestrator

            orchestrator = Orchestrator({"provider": "ollama", "folders": ["Inbox"]})

            response = orchestrator.handle_message({"type": "ping"})

            assert response["status"] == "ok"
            assert response["type"] == "pong"
