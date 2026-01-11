import atexit
import faulthandler
import os
import sys
import threading
import time
from typing import Optional


def _env_int(name: str, default: int) -> int:
    value = os.environ.get(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _start_watchdog(timeout_seconds: int) -> Optional[threading.Timer]:
    if timeout_seconds <= 0:
        return None

    def _kill() -> None:
        try:
            faulthandler.dump_traceback(file=sys.stderr, all_threads=True)
        except Exception:
            pass
        # Hard exit: guarantees CI can't hang forever.
        os._exit(2)

    timer = threading.Timer(timeout_seconds, _kill)
    timer.daemon = True
    timer.start()
    return timer


def pytest_sessionstart(session) -> None:  # noqa: ANN001
    # Always enable faulthandler for better diagnostics on timeouts/hangs.
    try:
        faulthandler.enable(all_threads=True)
    except Exception:
        pass

    # Absolute upper bound for the whole test run.
    # Default: 20 minutes (matches "never hang" requirement but leaves room for CI slowness).
    watchdog_seconds = _env_int("PYTEST_WATCHDOG_TIMEOUT_SECONDS", 20 * 60)
    timer = _start_watchdog(watchdog_seconds)

    if timer is not None:
        atexit.register(timer.cancel)

    # Minor guardrail: if a test suite is extremely slow, at least dump stacks periodically.
    # This doesn't stop execution, but helps debug if the watchdog triggers.
    dump_every = _env_int("PYTEST_DUMP_STACK_EVERY_SECONDS", 0)
    if dump_every > 0:
        _start_periodic_dump(dump_every)


def _start_periodic_dump(every_seconds: int) -> None:
    def _loop() -> None:
        while True:
            time.sleep(every_seconds)
            try:
                faulthandler.dump_traceback(file=sys.stderr, all_threads=True)
            except Exception:
                pass

    t = threading.Thread(target=_loop, daemon=True)
    t.start()
