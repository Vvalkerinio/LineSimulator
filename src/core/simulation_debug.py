from contextlib import contextmanager
from contextvars import ContextVar

_DEBUG_ENABLED = ContextVar("line_simulator_debug_enabled", default=False)

def is_debug_enabled() -> bool:
    return bool(_DEBUG_ENABLED.get())

def debug_print(message_factory=None) -> None:
    """Lazily emit one diagnostic line only when debug is enabled."""
    if not is_debug_enabled():
        return
    if message_factory is None:
        print()
        return
    message = message_factory() if callable(message_factory) else message_factory
    print(message)

@contextmanager
def debug_mode(enabled: bool = False):
    token = _DEBUG_ENABLED.set(bool(enabled))
    try:
        yield
    finally:
        _DEBUG_ENABLED.reset(token)
