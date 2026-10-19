import io
from contextlib import redirect_stdout
from src.core.simulation_debug import debug_mode, debug_print, is_debug_enabled

def test_debug_off_is_lazy_and_silent():
    calls=[]; output=io.StringIO()
    with redirect_stdout(output):
        debug_print(lambda: calls.append(1) or "hidden")
    assert calls == []
    assert output.getvalue() == ""
    assert is_debug_enabled() is False

def test_debug_on_prints_and_context_is_restored():
    output=io.StringIO()
    with redirect_stdout(output), debug_mode(True):
        debug_print(lambda: "visible")
    assert output.getvalue() == "visible\n"
    assert is_debug_enabled() is False
