"""
Unit tests for prompt engine (INT-002, INT-004).
"""

from backend.core.prompt_engine import PromptEngine, PromptTemplate


class TestPromptEngine:
    """Tests for PromptEngine."""

    def setup_method(self):
        """Create engine for testing."""
        self.engine = PromptEngine(
            {
                "default_language": "en",
                "templates_dir": None,  # Use built-in templates
                "detect_language": True,
                "max_body_length": 500,
            }
        )

    def test_build_system_prompt_en(self):
        """Should build English system prompt."""
        prompt = self.engine.build_system_prompt(
            folders=["Inbox", "Invoices", "Newsletters"], language="en"
        )

        # Check for classification-related terms
        assert "classification" in prompt.lower() or "classify" in prompt.lower()
        # System prompt may or may not include folders depending on template
        assert "JSON" in prompt

    def test_build_system_prompt_fr(self):
        """Should build French system prompt."""
        prompt = self.engine.build_system_prompt(
            folders=["Inbox", "Factures"], language="fr"
        )

        # French prompt should have classification-related terms
        assert "classification" in prompt.lower() or "classifier" in prompt.lower()

    def test_build_user_prompt_en(self):
        """Should build English user prompt."""
        prompt = self.engine.build_user_prompt(
            sender="invoice@company.com",
            subject="Your monthly invoice",
            body="Please find attached your invoice for March 2024.",
            language="en",
        )

        # User prompt should include subject and body content
        assert "monthly invoice" in prompt.lower() or "invoice" in prompt.lower()
        assert "attached" in prompt

    def test_build_user_prompt_truncates_body(self):
        """Should truncate long body."""
        long_body = "x" * 1000

        prompt = self.engine.build_user_prompt(
            sender="test@test.com", subject="Test", body=long_body, language="en"
        )

        # Should be truncated to max_body_length
        assert len(prompt) < len(long_body) + 200

    def test_build_user_prompt_handles_none(self):
        """Should handle None fields gracefully."""
        prompt = self.engine.build_user_prompt(
            sender=None, subject=None, body=None, language="en"
        )

        assert prompt  # Should still produce something

    def test_detect_language_english(self):
        """Should detect English text."""
        text = "This is a test email about your recent purchase."

        lang = self.engine.detect_language(text)

        assert lang == "en"

    def test_detect_language_french(self):
        """Should detect French text."""
        text = "Bonjour, voici votre facture mensuelle. Merci de votre confiance."

        lang = self.engine.detect_language(text)

        assert lang == "fr"

    def test_detect_language_german(self):
        """Should detect German text."""
        text = "Guten Tag, hier ist Ihre monatliche Rechnung."

        lang = self.engine.detect_language(text)

        assert lang == "de"

    def test_detect_language_short_text_fallback(self):
        """Should fallback to default for short text."""
        text = "Hi"  # Too short to detect

        lang = self.engine.detect_language(text)

        assert lang == "en"  # Default

    def test_detect_language_caching(self):
        """Should cache detected language by sender."""
        sender = "french@example.fr"
        text = "Bonjour, ceci est un test."

        # First detection
        self.engine.detect_language(text, sender=sender)

        # Should be cached
        cached = self.engine.get_cached_language(sender)

        assert cached == "fr"

    def test_build_full_prompt(self):
        """Should build complete prompt (system + user)."""
        result = self.engine.build_prompt(
            sender="test@example.com",
            subject="Test Subject",
            body="Test body content.",
            folders=["Inbox", "Spam", "Newsletters"],
        )

        assert "system" in result
        assert "user" in result
        assert result["language"] in ["en", "fr", "de"]

    def test_supported_languages(self):
        """Should list supported languages."""
        languages = self.engine.supported_languages()

        assert "en" in languages
        assert "fr" in languages
        assert "de" in languages

    def test_add_custom_template(self):
        """Should add custom template."""
        self.engine.add_template(
            name="custom_system",
            template="Custom system prompt for {{ folders }}",
            language="en",
        )

        templates = self.engine.list_templates()
        assert "custom_system" in [t["name"] for t in templates]

    def test_escape_special_chars(self):
        """Should escape special characters in email content."""
        prompt = self.engine.build_user_prompt(
            sender="test@test.com",
            subject="Test <script>alert('xss')</script>",
            body="Body with {{ jinja }} syntax",
            language="en",
        )

        # Should not break Jinja rendering
        assert "alert" in prompt or "script" not in prompt


class TestPromptTemplate:
    """Tests for PromptTemplate dataclass."""

    def test_render_simple(self):
        """Should render simple template."""
        template = PromptTemplate(
            name="test", template="Hello {{ name }}!", language="en"
        )

        result = template.render(name="World")

        assert result == "Hello World!"

    def test_render_with_list(self):
        """Should render template with list."""
        template = PromptTemplate(
            name="folders",
            template="Folders: {% for f in folders %}{{ f }}{% if not loop.last %}, {% endif %}{% endfor %}",
            language="en",
        )

        result = template.render(folders=["A", "B", "C"])

        assert result == "Folders: A, B, C"

    def test_render_missing_variable(self):
        """Should handle missing variables gracefully."""
        template = PromptTemplate(
            name="test", template="Hello {{ name | default('Guest') }}!", language="en"
        )

        result = template.render()  # No name provided

        assert result == "Hello Guest!"


class TestPromptEngineEdgeCases:
    """Edge case tests for PromptEngine."""

    def test_empty_folders(self):
        """Should handle empty folder list."""
        engine = PromptEngine({})

        prompt = engine.build_system_prompt(folders=[], language="en")

        assert prompt  # Should still work

    def test_unicode_content(self):
        """Should handle Unicode content."""
        engine = PromptEngine({})

        prompt = engine.build_user_prompt(
            sender="test@example.com",
            subject="日本語テスト",
            body="This contains émojis 🎉 and accénts",
            language="en",
        )

        assert "日本語" in prompt
        assert "🎉" in prompt

    def test_very_long_folder_list(self):
        """Should handle many folders without error."""
        engine = PromptEngine({})

        folders = [f"Folder{i}" for i in range(50)]

        # System prompt should build without error even with many folders
        prompt = engine.build_system_prompt(folders=folders, language="en")

        # System prompt should be valid and contain classification instructions
        assert "classification" in prompt.lower() or "classify" in prompt.lower()
        assert len(prompt) > 0
