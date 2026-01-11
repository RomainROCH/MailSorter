"""
Unit tests for smart cache (cost optimization).
"""

import time

from backend.core.smart_cache import SmartCache, CacheEntry


class TestSmartCache:
    """Tests for SmartCache."""

    def setup_method(self):
        """Create cache for testing."""
        self.cache = SmartCache(
            {
                "enabled": True,
                "rule_cache_enabled": True,
                "sender_cache_enabled": True,
                "hash_cache_enabled": True,
                "sender_cache_ttl": 86400,  # 1 day for testing
                "hash_cache_ttl": 3600,  # 1 hour for testing
                "max_entries": 100,
                "use_default_rules": False,  # Don't load default rules for testing
            }
        )

    def test_disabled_cache(self):
        """Should not cache when disabled."""
        cache = SmartCache({"enabled": False})

        # Try to cache
        cache.cache_by_sender("test@example.com", "Invoices", 0.9)

        # Should not find
        result = cache.lookup_by_sender("test@example.com")
        assert result is None

    # === Rule Cache Tests ===

    def test_add_rule(self):
        """Should add classification rule."""
        self.cache.add_rule(pattern=r".*@amazon\.com$", folder="Shopping", priority=1)

        rules = self.cache.list_rules()
        assert len(rules) == 1
        assert rules[0]["folder"] == "Shopping"

    def test_rule_match(self):
        """Should match rule by pattern."""
        self.cache.add_rule(
            pattern=r".*invoice.*", folder="Invoices", priority=1, match_field="subject"
        )

        result = self.cache.check_rules(
            sender="billing@company.com", subject="Your invoice #12345"
        )

        assert result is not None
        assert result["folder"] == "Invoices"

    def test_rule_priority(self):
        """Should respect rule priority (higher = first)."""
        self.cache.add_rule(pattern=r".*", folder="Catch-All", priority=0)
        self.cache.add_rule(pattern=r".*@vip\.com$", folder="VIP", priority=10)

        result = self.cache.check_rules(sender="ceo@vip.com")

        assert result["folder"] == "VIP"

    def test_rule_no_match(self):
        """Should return None when no rules match."""
        self.cache.add_rule(pattern=r".*@amazon\.com$", folder="Shopping")

        result = self.cache.check_rules(sender="john@gmail.com")
        assert result is None

    def test_remove_rule(self):
        """Should remove rule by ID."""
        self.cache.add_rule(pattern=r".*", folder="Test", rule_id="test-rule")
        self.cache.remove_rule("test-rule")

        rules = self.cache.list_rules()
        assert len(rules) == 0

    # === Sender Cache Tests ===

    def test_cache_by_sender(self):
        """Should cache by sender."""
        self.cache.cache_by_sender("invoice@company.com", "Invoices", 0.95)

        result = self.cache.lookup_by_sender("invoice@company.com")

        assert result is not None
        assert result.folder == "Invoices"
        assert result.confidence == 0.95

    def test_sender_cache_case_insensitive(self):
        """Should be case-insensitive for sender."""
        self.cache.cache_by_sender("Test@Example.COM", "Test", 0.8)

        result = self.cache.lookup_by_sender("test@example.com")
        assert result is not None

    def test_sender_cache_updates(self):
        """Should update existing sender cache."""
        self.cache.cache_by_sender("sender@test.com", "Folder1", 0.7)
        self.cache.cache_by_sender("sender@test.com", "Folder2", 0.9)

        result = self.cache.lookup_by_sender("sender@test.com")

        assert result.folder == "Folder2"
        assert result.confidence == 0.9

    def test_sender_cache_miss(self):
        """Should return None for unknown sender."""
        result = self.cache.lookup_by_sender("unknown@example.com")
        assert result is None

    # === Hash Cache Tests ===

    def test_cache_by_hash(self):
        """Should cache by content hash."""
        content_hash = "abc123def456"
        self.cache.cache_by_hash(content_hash, "Newsletters", 0.88)

        result = self.cache.lookup_by_hash(content_hash)

        assert result is not None
        assert result.folder == "Newsletters"

    def test_compute_email_hash(self):
        """Should compute consistent hash."""
        email = {
            "sender": "test@example.com",
            "subject": "Hello World",
            "body": "This is a test email",
        }

        hash1 = self.cache.compute_email_hash(email)
        hash2 = self.cache.compute_email_hash(email)

        assert hash1 == hash2
        assert len(hash1) == 64  # SHA-256

    def test_hash_ignores_whitespace(self):
        """Should normalize whitespace in hash."""
        email1 = {"subject": "Hello   World", "body": "  Test  "}
        email2 = {"subject": "Hello World", "body": "Test"}

        hash1 = self.cache.compute_email_hash(email1)
        hash2 = self.cache.compute_email_hash(email2)

        assert hash1 == hash2

    # === Combined Lookup ===

    def test_lookup_combined_rules_first(self):
        """Should check rules before sender cache."""
        self.cache.add_rule(pattern=r".*@priority\.com$", folder="Priority")
        self.cache.cache_by_sender("user@priority.com", "Regular", 0.9)

        result = self.cache.lookup(sender="user@priority.com", subject="Test")

        assert result is not None
        assert result["folder"] == "Priority"
        assert result["source"] == "rule"

    def test_lookup_combined_fallback_sender(self):
        """Should fallback to sender cache if no rules match."""
        self.cache.cache_by_sender("known@example.com", "KnownSender", 0.85)

        result = self.cache.lookup(sender="known@example.com")

        assert result["folder"] == "KnownSender"
        assert result["source"] == "sender_cache"

    def test_lookup_combined_fallback_hash(self):
        """Should fallback to hash cache."""
        email_hash = "test-hash-123"
        self.cache.cache_by_hash(email_hash, "Cached", 0.9)

        result = self.cache.lookup(
            sender="unknown@example.com", content_hash=email_hash
        )

        assert result["folder"] == "Cached"
        assert result["source"] == "hash_cache"

    # === Statistics ===

    def test_stats(self):
        """Should track cache statistics."""
        # Generate some hits and misses
        self.cache.cache_by_sender("hit@test.com", "Test", 0.9)
        self.cache.lookup_by_sender("hit@test.com")  # Hit
        self.cache.lookup_by_sender("miss@test.com")  # Miss

        stats = self.cache.get_stats()

        assert stats["sender_cache"]["hits"] == 1
        assert stats["sender_cache"]["misses"] == 1

    def test_clear_cache(self):
        """Should clear all cache entries."""
        self.cache.cache_by_sender("test@test.com", "Test", 0.9)
        self.cache.cache_by_hash("hash123", "Test", 0.9)

        self.cache.clear()

        assert self.cache.lookup_by_sender("test@test.com") is None
        assert self.cache.lookup_by_hash("hash123") is None


class TestCacheEntry:
    """Tests for CacheEntry dataclass."""

    def test_not_expired(self):
        """Should not be expired immediately."""
        entry = CacheEntry(
            folder="Test", confidence=0.9, created_at=time.time(), ttl=3600
        )

        assert entry.is_expired() is False

    def test_expired(self):
        """Should be expired after TTL."""
        entry = CacheEntry(
            folder="Test",
            confidence=0.9,
            created_at=time.time() - 7200,  # 2 hours ago
            ttl=3600,  # 1 hour TTL
        )

        assert entry.is_expired() is True

    def test_no_expiry(self):
        """Should never expire with TTL=0."""
        entry = CacheEntry(
            folder="Test", confidence=0.9, created_at=0, ttl=0  # Very old  # No expiry
        )

        assert entry.is_expired() is False
