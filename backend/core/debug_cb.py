from backend.core.circuit_breaker import CircuitBreaker
import time

if __name__ == "__main__":
    b = CircuitBreaker(failure_threshold=3, recovery_timeout=1.0, success_threshold=1)
    for _ in range(3):
        b.record_failure("test_provider")
    print("after failures state:", b.get_state("test_provider"))
    print("can_execute:", b.can_execute("test_provider"))
    time.sleep(1.1)
    print("after sleep state:", b.get_state("test_provider"))
    print("can_execute:", b.can_execute("test_provider"))
    b.record_success("test_provider")
    print("after record_success state:", b.get_state("test_provider"))
    print("stats:", b.get_stats("test_provider"))
