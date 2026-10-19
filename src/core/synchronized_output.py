import io
import sys
import threading
from contextlib import contextmanager, redirect_stdout


_STDOUT_REDIRECT_LOCK = threading.RLock()


def usable_stdout():
    """Return a writable stdout, never a closed redirected stream."""
    candidates = (sys.stdout, sys.__stdout__)
    for candidate in candidates:
        if candidate is None:
            continue
        try:
            if getattr(candidate, "closed", False):
                continue
            candidate.flush()
            return candidate
        except (ValueError, OSError, AttributeError):
            continue
    return io.StringIO()


@contextmanager
def synchronized_redirect_stdout(target):
    """Serialize process-global stdout redirection across worker threads."""
    with _STDOUT_REDIRECT_LOCK:
        previous = usable_stdout()
        sys.stdout = previous
        try:
            with redirect_stdout(target):
                yield target
        finally:
            sys.stdout = previous


@contextmanager
def synchronized_suppress_stdout():
    """Capture noisy simulation output without using a closeable OS stream."""
    sink = io.StringIO()
    with synchronized_redirect_stdout(sink):
        yield sink
