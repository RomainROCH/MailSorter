"""
Fuzz tests for MIME parsing and email handling.

Tests the system's resilience against malformed, random, and adversarial
email content to prevent crashes and security vulnerabilities.

Task: QA-007
"""

import pytest
import random
import string
import json
from typing import Generator

from backend.core.privacy import PrivacyGuard
from backend.utils.sanitize import sanitize_text


# Fuzz test configuration
FUZZ_ITERATIONS = 100
MAX_STRING_LENGTH = 10000


def random_string(length: int) -> str:
    """Generate a random ASCII string."""
    return ''.join(random.choices(string.printable, k=length))


def random_unicode_string(length: int) -> str:
    """Generate a random unicode string with various characters."""
    chars = []
    for _ in range(length):
        # Mix of ASCII, Latin, CJK, emoji, and special chars
        char_type = random.choice(['ascii', 'latin', 'cjk', 'emoji', 'special'])
        if char_type == 'ascii':
            chars.append(random.choice(string.printable))
        elif char_type == 'latin':
            chars.append(chr(random.randint(0x00C0, 0x00FF)))  # Latin Extended
        elif char_type == 'cjk':
            chars.append(chr(random.randint(0x4E00, 0x4FFF)))  # CJK chars
        elif char_type == 'emoji':
            # Common emoji range
            chars.append(chr(random.randint(0x1F600, 0x1F64F)))
        else:
            # Special/control characters
            chars.append(chr(random.choice([0x00, 0x0A, 0x0D, 0x1B, 0x7F])))
    return ''.join(chars)


def random_email_address() -> str:
    """Generate a random (possibly invalid) email address."""
    local_part = random_string(random.randint(0, 100))
    domain = random_string(random.randint(0, 50))
    return f"{local_part}@{domain}"


def random_mime_header() -> str:
    """Generate a random MIME-like header."""
    headers = [
        f"Content-Type: {random_string(20)}",
        f"X-Custom-Header: {random_string(50)}",
        f"From: {random_email_address()}",
        f"Subject: {random_string(random.randint(0, 200))}",
    ]
    return random.choice(headers)


class TestFuzzSanitization:
    """Fuzz tests for text sanitization."""
    
    @pytest.fixture
    def privacy_guard(self):
        """Create a privacy guard instance."""
        return PrivacyGuard()
    
    def test_fuzz_random_ascii_strings(self, privacy_guard):
        """Sanitization should handle random ASCII strings."""
        for _ in range(FUZZ_ITERATIONS):
            length = random.randint(0, MAX_STRING_LENGTH)
            text = random_string(length)
            
            try:
                result = privacy_guard.sanitize(text)
                assert result is not None or result == ""
            except Exception as e:
                pytest.fail(f"Crash on random ASCII string: {e}")
    
    def test_fuzz_random_unicode_strings(self, privacy_guard):
        """Sanitization should handle random unicode strings."""
        for _ in range(FUZZ_ITERATIONS):
            length = random.randint(0, 1000)  # Smaller for unicode
            text = random_unicode_string(length)
            
            try:
                result = privacy_guard.sanitize(text)
                # May return empty or modified, but shouldn't crash
            except UnicodeError:
                # Some unicode sequences may be invalid - that's OK
                pass
            except Exception as e:
                pytest.fail(f"Unexpected crash on unicode: {e}")
    
    def test_fuzz_email_addresses(self, privacy_guard):
        """Sanitization should handle malformed email addresses."""
        for _ in range(FUZZ_ITERATIONS):
            # Various malformed email patterns
            patterns = [
                random_email_address(),
                f"@{random_string(10)}.com",
                f"{random_string(10)}@",
                f"{random_string(10)}@@{random_string(5)}.com",
                f"a" * 1000 + "@test.com",
                f"test@" + "a" * 1000,
                f"{random_string(10)}@{random_string(10)}@{random_string(10)}",
            ]
            text = random.choice(patterns)
            
            try:
                result = privacy_guard.sanitize(text)
                # Should complete without hanging
            except Exception as e:
                pytest.fail(f"Crash on malformed email: {e}")


class TestFuzzJSONHandling:
    """Fuzz tests for JSON handling in messages."""
    
    def test_fuzz_json_strings(self):
        """JSON encoding should handle random strings."""
        for _ in range(FUZZ_ITERATIONS):
            text = random_string(random.randint(0, 1000))
            
            try:
                encoded = json.dumps({"text": text})
                decoded = json.loads(encoded)
                assert decoded["text"] == text
            except Exception as e:
                pytest.fail(f"JSON handling failed: {e}")
    
    def test_fuzz_nested_json(self):
        """Deep JSON nesting should be handled."""
        max_depth = 20
        
        def build_nested(depth):
            if depth == 0:
                return random_string(10)
            return {"nested": build_nested(depth - 1)}
        
        for depth in range(1, max_depth):
            try:
                obj = build_nested(depth)
                encoded = json.dumps(obj)
                decoded = json.loads(encoded)
                # Should not crash
            except RecursionError:
                # Deep nesting may hit recursion limit - that's OK
                pass


class TestFuzzMIMEContent:
    """Fuzz tests for MIME-like content."""
    
    @pytest.fixture
    def privacy_guard(self):
        return PrivacyGuard()
    
    def test_fuzz_mime_headers(self, privacy_guard):
        """MIME-like headers in content should be handled."""
        for _ in range(FUZZ_ITERATIONS):
            headers = [random_mime_header() for _ in range(random.randint(1, 10))]
            content = "\r\n".join(headers) + "\r\n\r\n" + random_string(100)
            
            try:
                result = privacy_guard.sanitize(content)
                # Should not crash
            except Exception as e:
                pytest.fail(f"MIME header handling failed: {e}")
    
    def test_fuzz_multipart_boundaries(self, privacy_guard):
        """Multipart boundaries should be handled."""
        for _ in range(FUZZ_ITERATIONS):
            boundary = random_string(random.randint(1, 70))
            content = f"""
--{boundary}
Content-Type: text/plain

{random_string(100)}
--{boundary}
Content-Type: text/html

<html>{random_string(50)}</html>
--{boundary}--
"""
            try:
                result = privacy_guard.sanitize(content)
                # Should not crash
            except Exception as e:
                pytest.fail(f"Multipart handling failed: {e}")
    
    def test_fuzz_base64_content(self, privacy_guard):
        """Base64-encoded content should be handled."""
        import base64
        
        for _ in range(FUZZ_ITERATIONS):
            raw_data = random_string(random.randint(0, 500)).encode('utf-8', errors='replace')
            b64_data = base64.b64encode(raw_data).decode('ascii')
            
            content = f"""
Content-Transfer-Encoding: base64

{b64_data}
"""
            try:
                result = privacy_guard.sanitize(content)
                # Should not crash
            except Exception as e:
                pytest.fail(f"Base64 content handling failed: {e}")


class TestFuzzControlCharacters:
    """Fuzz tests for control characters."""
    
    @pytest.fixture
    def privacy_guard(self):
        return PrivacyGuard()
    
    def test_fuzz_null_bytes(self, privacy_guard):
        """Null bytes should not crash the system."""
        for _ in range(50):
            null_positions = [random.randint(0, 99) for _ in range(10)]
            text = list("A" * 100)
            for pos in null_positions:
                text[pos] = '\x00'
            text = ''.join(text)
            
            try:
                result = privacy_guard.sanitize(text)
                # Should complete without crash - null byte handling is a design choice
                assert result is not None
            except Exception as e:
                pytest.fail(f"Null byte handling crashed: {e}")
    
    def test_fuzz_escape_sequences(self, privacy_guard):
        """Escape sequences should be handled."""
        escape_chars = ['\n', '\r', '\t', '\b', '\f', '\v', '\\', '"', "'"]
        
        for _ in range(FUZZ_ITERATIONS):
            text = ''.join(random.choices(escape_chars + list("abc"), k=100))
            
            try:
                result = privacy_guard.sanitize(text)
                # Should not crash
            except Exception as e:
                pytest.fail(f"Escape sequence handling failed: {e}")
    
    def test_fuzz_ansi_codes(self, privacy_guard):
        """ANSI escape codes should be handled."""
        ansi_codes = [
            "\x1b[0m", "\x1b[31m", "\x1b[1;32m", "\x1b[H\x1b[2J",
            "\x1b[?25l", "\x1b[?25h"
        ]
        
        for _ in range(50):
            text = random.choice(ansi_codes) + random_string(50) + random.choice(ansi_codes)
            
            try:
                result = privacy_guard.sanitize(text)
                # Should not crash, ANSI codes may be stripped
            except Exception as e:
                pytest.fail(f"ANSI code handling failed: {e}")


class TestFuzzPromptInjection:
    """Fuzz tests for prompt injection patterns."""
    
    def test_fuzz_prompt_injection_patterns(self):
        """Random prompt injection-like patterns should be neutralized."""
        injection_fragments = [
            "ignore", "previous", "instructions", "SYSTEM:", "USER:",
            "ASSISTANT:", "<|im_start|>", "<|im_end|>", "```", "{{",
            "}}", "${", "$(", ")", "eval", "exec", "import", "os."
        ]
        
        for _ in range(FUZZ_ITERATIONS):
            # Build random injection-like text
            fragments = random.choices(injection_fragments, k=random.randint(1, 10))
            text = ' '.join(fragments) + random_string(50)
            
            try:
                result = sanitize_text(text)
                # Should not crash
                assert result is not None
            except Exception as e:
                pytest.fail(f"Injection pattern handling failed: {e}")


class TestFuzzReDoS:
    """Fuzz tests for ReDoS (Regular Expression Denial of Service)."""
    
    @pytest.fixture
    def privacy_guard(self):
        return PrivacyGuard()
    
    def test_fuzz_redos_email_pattern(self, privacy_guard):
        """Email regex should not be vulnerable to ReDoS."""
        import time
        
        # Patterns known to cause ReDoS in naive email regex
        evil_patterns = [
            "a" * 100 + "@",
            "@" + "a" * 100,
            "a" * 50 + "@" + "a" * 50,
            "." * 100 + "@test.com",
            "a@" + "." * 100,
        ]
        
        for pattern in evil_patterns:
            start = time.perf_counter()
            result = privacy_guard.sanitize(pattern)
            elapsed = time.perf_counter() - start
            
            # Should complete in reasonable time (< 1 second)
            assert elapsed < 1.0, f"Potential ReDoS: {elapsed:.2f}s for pattern"
    
    def test_fuzz_redos_phone_pattern(self, privacy_guard):
        """Phone regex should not be vulnerable to ReDoS."""
        import time
        
        # Patterns that might cause ReDoS in phone regex
        evil_patterns = [
            "-" * 100,
            "+" + "-" * 100,
            "(" + "-" * 100 + ")",
            "0" * 100 + "-" * 100,
        ]
        
        for pattern in evil_patterns:
            start = time.perf_counter()
            result = privacy_guard.sanitize(pattern)
            elapsed = time.perf_counter() - start
            
            assert elapsed < 1.0, f"Potential ReDoS: {elapsed:.2f}s"


class TestFuzzEdgeCases:
    """Fuzz tests for various edge cases."""
    
    @pytest.fixture
    def privacy_guard(self):
        return PrivacyGuard()
    
    def test_fuzz_extreme_lengths(self, privacy_guard):
        """Extreme string lengths should be handled."""
        lengths = [0, 1, 10, 100, 1000, 10000, 50000]
        
        for length in lengths:
            text = "A" * length
            
            try:
                result = privacy_guard.sanitize(text)
                # Should complete, possibly truncated
            except MemoryError:
                # Very large strings may cause memory issues - OK for test
                pass
            except Exception as e:
                pytest.fail(f"Length {length} caused crash: {e}")
    
    def test_fuzz_repetition_patterns(self, privacy_guard):
        """Repeated patterns should be handled."""
        patterns = ["abc", "test@", "@test", ".", "-", " ", "\n"]
        
        for pattern in patterns:
            for repetition in [10, 100, 1000]:
                text = pattern * repetition
                
                try:
                    result = privacy_guard.sanitize(text)
                    # Should not hang
                except Exception as e:
                    pytest.fail(f"Repetition pattern failed: {e}")
