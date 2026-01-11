"""
Unit tests for circuit breaker (AUDIT-003).
"""

import time

from backend.core.circuit_breaker import (
    CircuitBreaker,
    CircuitState,
    get_circuit_breaker,
    reset_circuit_breaker,
)


class TestCircuitBreaker:
    """Tests for CircuitBreaker implementation."""

    def setup_method(self):
        """Create fresh circuit breaker for each test."""
        self.breaker = CircuitBreaker(
            failure_threshold=3,
            recovery_timeout=1.0,  # Short for testing
            success_threshold=1,
        )

    def test_initial_state_closed(self):
        """Circuit should start in CLOSED state."""
        state = self.breaker.get_state("test_provider")
        assert state == CircuitState.CLOSED

    def test_can_execute_when_closed(self):
        """Should allow execution when circuit is closed."""
        assert self.breaker.can_execute("test_provider") is True

    def test_single_failure_stays_closed(self):
        """Single failure should not open circuit."""
        self.breaker.record_failure("test_provider")

        assert self.breaker.get_state("test_provider") == CircuitState.CLOSED
        assert self.breaker.can_execute("test_provider") is True

    def test_multiple_failures_opens_circuit(self):
        """Consecutive failures should open circuit."""
        for _ in range(3):
            self.breaker.record_failure("test_provider")

        assert self.breaker.get_state("test_provider") == CircuitState.OPEN
        assert self.breaker.can_execute("test_provider") is False

    def test_success_resets_failure_count(self):
        """Success should reset failure counter."""
        self.breaker.record_failure("test_provider")
        self.breaker.record_failure("test_provider")
        self.breaker.record_success("test_provider")
        self.breaker.record_failure("test_provider")

        # Should still be closed (only 1 consecutive failure)
        assert self.breaker.get_state("test_provider") == CircuitState.CLOSED

    def test_recovery_timeout_to_half_open(self):
        """After timeout, circuit should transition to HALF_OPEN."""
        # Open the circuit
        for _ in range(3):
            self.breaker.record_failure("test_provider")

        assert self.breaker.get_state("test_provider") == CircuitState.OPEN

        # Wait for recovery timeout
        time.sleep(1.1)

        # Should now be HALF_OPEN
        assert self.breaker.get_state("test_provider") == CircuitState.HALF_OPEN
        assert self.breaker.can_execute("test_provider") is True

    def test_success_in_half_open_closes_circuit(self):
        """Success in HALF_OPEN should close circuit."""
        # Open then transition to half-open
        for _ in range(3):
            self.breaker.record_failure("test_provider")
        time.sleep(1.1)

        # Record success
        self.breaker.record_success("test_provider")

        assert self.breaker.get_state("test_provider") == CircuitState.CLOSED

    def test_failure_in_half_open_opens_circuit(self):
        """Failure in HALF_OPEN should reopen circuit."""
        # Open then transition to half-open
        for _ in range(3):
            self.breaker.record_failure("test_provider")
        time.sleep(1.1)

        assert self.breaker.get_state("test_provider") == CircuitState.HALF_OPEN

        # Record failure
        self.breaker.record_failure("test_provider")

        assert self.breaker.get_state("test_provider") == CircuitState.OPEN

    def test_get_stats(self):
        """Should return comprehensive statistics."""
        self.breaker.record_success("test_provider")
        self.breaker.record_failure("test_provider")

        stats = self.breaker.get_stats("test_provider")

        assert stats["provider"] == "test_provider"
        assert stats["state"] == "closed"
        assert stats["total_calls"] == 2
        assert stats["total_failures"] == 1

    def test_reset(self):
        """Should reset circuit to initial state."""
        for _ in range(3):
            self.breaker.record_failure("test_provider")

        assert self.breaker.get_state("test_provider") == CircuitState.OPEN

        self.breaker.reset("test_provider")

        assert self.breaker.get_state("test_provider") == CircuitState.CLOSED

    def test_fallback_folder(self):
        """Should provide fallback folder."""
        assert self.breaker.get_fallback_folder() == "Inbox"

    def test_execute_with_fallback_success(self):
        """Should execute function and return result on success."""

        def success_fn():
            return "result"

        result = self.breaker.execute_with_fallback(
            "test_provider", success_fn, fallback="fallback"
        )

        assert result == "result"

    def test_execute_with_fallback_on_failure(self):
        """Should return fallback on function failure."""

        def failing_fn():
            raise Exception("Test error")

        result = self.breaker.execute_with_fallback(
            "test_provider", failing_fn, fallback="fallback_value"
        )

        assert result == "fallback_value"

    def test_execute_with_fallback_when_open(self):
        """Should return fallback immediately when circuit is open."""
        # Open the circuit
        for _ in range(3):
            self.breaker.record_failure("test_provider")

        call_count = 0

        def counting_fn():
            nonlocal call_count
            call_count += 1
            return "result"

        result = self.breaker.execute_with_fallback(
            "test_provider", counting_fn, fallback="fallback"
        )

        assert result == "fallback"
        assert call_count == 0  # Function should not have been called

    def test_independent_circuits_per_provider(self):
        """Each provider should have independent circuit."""
        # Open circuit for provider1
        for _ in range(3):
            self.breaker.record_failure("provider1")

        assert self.breaker.can_execute("provider1") is False
        assert self.breaker.can_execute("provider2") is True


class TestGlobalCircuitBreaker:
    """Tests for global circuit breaker instance."""

    def setup_method(self):
        reset_circuit_breaker()

    def teardown_method(self):
        reset_circuit_breaker()

    def test_get_circuit_breaker_singleton(self):
        """Should return same instance."""
        breaker1 = get_circuit_breaker()
        breaker2 = get_circuit_breaker()

        assert breaker1 is breaker2

    def test_reset_creates_new_instance(self):
        """Reset should create new instance on next get."""
        breaker1 = get_circuit_breaker()
        reset_circuit_breaker()
        breaker2 = get_circuit_breaker()

        assert breaker1 is not breaker2
