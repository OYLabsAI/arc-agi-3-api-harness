"""POSIX wall-clock guards for the synchronous, main-thread evaluator."""

from __future__ import annotations

import math
import signal
import threading
import time
from contextlib import contextmanager

from .api_budget import BudgetStop


class DeadlineExpired(KeyboardInterrupt):
    """Bypass SDK Exception handlers so an expired call cannot continue/retry."""


@contextmanager
def wall_timeout(seconds, reason="operation_deadline"):
    if not math.isfinite(seconds) or seconds <= 0:
        raise BudgetStop(reason)
    if not hasattr(signal, "setitimer") or threading.current_thread() is not threading.main_thread():
        raise RuntimeError("Wall deadlines require the POSIX evaluator main thread")
    old_handler = signal.getsignal(signal.SIGALRM)
    old_seconds, interval = signal.getitimer(signal.ITIMER_REAL)
    # Keep an earlier surrounding deadline authoritative, including its handler.
    if old_seconds and old_seconds <= seconds:
        yield
        return
    started = time.monotonic()

    def expired(signum, frame):
        raise DeadlineExpired(reason)

    signal.signal(signal.SIGALRM, expired)
    signal.setitimer(signal.ITIMER_REAL, seconds)
    try:
        yield
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, old_handler)
        remaining = old_seconds - (time.monotonic() - started)
        if old_seconds and remaining > 0:
            signal.setitimer(signal.ITIMER_REAL, remaining, interval)
