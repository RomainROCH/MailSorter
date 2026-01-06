"""
Circuit breaker for LLM provider resilience.

Implements AUDIT-003: 3 failures = open circuit, 30s cooldown, fallback to Inbox.
Prevents cascading failures and wasted API calls during outages.
"""

import logging
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Dict, Optional, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"      # Normal operation, calls allowed
    OPEN = "open"          # Failing, calls rejected
    HALF_OPEN = "half_open"  # Testing recovery


@dataclass
class CircuitStats:
    """Statistics for a circuit."""
    failures: int = 0
    successes: int = 0
    last_failure: float = 0.0
    last_success: float = 0.0
    state: CircuitState = CircuitState.CLOSED
    total_calls: int = 0
    total_failures: int = 0


class CircuitBreaker:
    """
    Circuit breaker implementation for provider resilience.
    
    Behavior:
    - CLOSED: Normal operation, all calls pass through
    - OPEN: After failure_threshold consecutive failures, reject all calls
    - HALF_OPEN: After recovery_timeout, allow one test call
    - If test succeeds, go CLOSED; if fails, go OPEN again
    
    Usage:
        breaker = CircuitBreaker()
        
        if breaker.can_execute("openai"):
            try:
                result = provider.classify_email(...)
                breaker.record_success("openai")
            except Exception:
                breaker.record_failure("openai")
                result = breaker.get_fallback_result()
    """
    
    def __init__(
        self,
        failure_threshold: int = 3,
        recovery_timeout: float = 30.0,
        success_threshold: int = 1
    ):
        """
        Initialize circuit breaker.
        
        Args:
            failure_threshold: Consecutive failures to open circuit
            recovery_timeout: Seconds before attempting recovery
            success_threshold: Successes needed to close circuit from half-open
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.success_threshold = success_threshold
        
        self._circuits: Dict[str, CircuitStats] = {}
        self._lock = threading.Lock()
    
    def get_state(self, provider: str) -> CircuitState:
        """
        Get current circuit state for provider.
        
        Also handles automatic transition from OPEN to HALF_OPEN
        when recovery timeout has elapsed.
        """
        with self._lock:
            stats = self._circuits.get(provider, CircuitStats())
            
            if stats.state == CircuitState.OPEN:
                # Check if recovery timeout has elapsed
                elapsed = time.time() - stats.last_failure
                if elapsed >= self.recovery_timeout:
                    stats.state = CircuitState.HALF_OPEN
                    stats.successes = 0  # Reset success counter for half-open test
                    self._circuits[provider] = stats
                    logger.info(f"Circuit HALF_OPEN for {provider} (testing recovery)")
            
            return stats.state
    
    def can_execute(self, provider: str) -> bool:
        """
        Check if calls are allowed for provider.
        
        Returns:
            True if circuit is CLOSED or HALF_OPEN
        """
        state = self.get_state(provider)
        return state != CircuitState.OPEN
    
    def record_success(self, provider: str) -> None:
        """
        Record a successful call.
        
        In HALF_OPEN state, may transition to CLOSED.
        In CLOSED state, resets failure counter.
        """
        with self._lock:
            stats = self._circuits.get(provider, CircuitStats())
            stats.successes += 1
            stats.last_success = time.time()
            stats.total_calls += 1
            stats.failures = 0  # Reset consecutive failure count
            
            if stats.state == CircuitState.HALF_OPEN:
                if stats.successes >= self.success_threshold:
                    stats.state = CircuitState.CLOSED
                    logger.info(f"Circuit CLOSED for {provider} (recovered)")
            
            self._circuits[provider] = stats
    
    def record_failure(self, provider: str) -> None:
        """
        Record a failed call.
        
        May transition to OPEN if failure threshold reached.
        """
        with self._lock:
            stats = self._circuits.get(provider, CircuitStats())
            stats.failures += 1
            stats.last_failure = time.time()
            stats.total_calls += 1
            stats.total_failures += 1
            stats.successes = 0  # Reset consecutive success count
            
            if stats.state == CircuitState.HALF_OPEN:
                # Any failure in half-open immediately opens circuit
                stats.state = CircuitState.OPEN
                logger.warning(f"Circuit OPEN for {provider} (recovery failed)")
            elif stats.failures >= self.failure_threshold:
                stats.state = CircuitState.OPEN
                logger.warning(
                    f"Circuit OPEN for {provider} after {stats.failures} consecutive failures"
                )
            
            self._circuits[provider] = stats
    
    def get_stats(self, provider: str) -> Dict:
        """
        Get statistics for a provider's circuit.
        
        Returns:
            Dict with state, counters, and timing info
        """
        with self._lock:
            stats = self._circuits.get(provider, CircuitStats())
            state = self.get_state(provider)  # May update state
            
            result = {
                "provider": provider,
                "state": state.value,
                "consecutive_failures": stats.failures,
                "consecutive_successes": stats.successes,
                "total_calls": stats.total_calls,
                "total_failures": stats.total_failures,
                "last_failure": stats.last_failure,
                "last_success": stats.last_success,
            }
            
            if state == CircuitState.OPEN:
                remaining = self.recovery_timeout - (time.time() - stats.last_failure)
                result["recovery_in_seconds"] = max(0, remaining)
            
            return result
    
    def reset(self, provider: str) -> None:
        """
        Manually reset a circuit to CLOSED state.
        
        Useful for admin override or testing.
        """
        with self._lock:
            self._circuits[provider] = CircuitStats()
            logger.info(f"Circuit manually reset for {provider}")
    
    def reset_all(self) -> None:
        """Reset all circuits to CLOSED state."""
        with self._lock:
            self._circuits.clear()
            logger.info("All circuits reset")
    
    def execute_with_fallback(
        self,
        provider: str,
        func: Callable[[], T],
        fallback: T
    ) -> T:
        """
        Execute function with circuit breaker protection and fallback.
        
        Args:
            provider: Provider name
            func: Function to execute
            fallback: Value to return if circuit is open or function fails
        
        Returns:
            Function result or fallback value
        """
        if not self.can_execute(provider):
            logger.debug(f"Circuit open for {provider}, returning fallback")
            return fallback
        
        try:
            result = func()
            self.record_success(provider)
            return result
        except Exception as e:
            logger.warning(f"Call failed for {provider}: {e}")
            self.record_failure(provider)
            return fallback
    
    @staticmethod
    def get_fallback_folder() -> str:
        """
        Get the safe fallback folder when circuit is open.
        
        Returns:
            "Inbox" as the universal safe fallback
        """
        return "Inbox"


# Global circuit breaker instance
_circuit_breaker: Optional[CircuitBreaker] = None
_circuit_lock = threading.Lock()


def get_circuit_breaker(
    failure_threshold: int = 3,
    recovery_timeout: float = 30.0
) -> CircuitBreaker:
    """
    Get or create the global circuit breaker instance.
    
    Args:
        failure_threshold: Consecutive failures to open circuit
        recovery_timeout: Seconds before attempting recovery
    
    Returns:
        Global CircuitBreaker instance
    """
    global _circuit_breaker
    
    with _circuit_lock:
        if _circuit_breaker is None:
            _circuit_breaker = CircuitBreaker(
                failure_threshold=failure_threshold,
                recovery_timeout=recovery_timeout
            )
        return _circuit_breaker


def reset_circuit_breaker() -> None:
    """Reset the global circuit breaker (mainly for testing)."""
    global _circuit_breaker
    with _circuit_lock:
        _circuit_breaker = None
