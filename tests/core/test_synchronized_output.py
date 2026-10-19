import io
import sys
import threading
import time

from src.core.synchronized_output import (
    synchronized_redirect_stdout,
    synchronized_suppress_stdout,
    usable_stdout,
)


def test_closed_stdout_is_never_restored():
    original = sys.stdout
    closed = io.StringIO()
    closed.close()
    try:
        sys.stdout = closed
        with synchronized_suppress_stdout() as captured:
            print("optimization")
        assert captured.getvalue() == "optimization\n"
        assert usable_stdout() is not None
        assert not getattr(usable_stdout(), "closed", False)
    finally:
        sys.stdout = original


def test_nested_redirects_restore_original_stream():
    original = sys.stdout
    outer = io.StringIO()
    inner = io.StringIO()
    with synchronized_redirect_stdout(outer):
        print("before")
        with synchronized_redirect_stdout(inner):
            print("inside")
        print("after")
    assert "before" in outer.getvalue()
    assert "after" in outer.getvalue()
    assert "inside" in inner.getvalue()
    assert sys.stdout is original


def test_threaded_redirects_do_not_leak_closed_stream():
    original = sys.stdout
    outputs = [io.StringIO(), io.StringIO()]
    errors = []

    def worker(index):
        try:
            with synchronized_redirect_stdout(outputs[index]):
                print(f"worker-{index}")
                time.sleep(0.02)
        except Exception as exc:
            errors.append(exc)

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert errors == []
    assert "worker-0" in outputs[0].getvalue()
    assert "worker-1" in outputs[1].getvalue()
    assert sys.stdout is original
    assert not getattr(sys.stdout, "closed", False)
