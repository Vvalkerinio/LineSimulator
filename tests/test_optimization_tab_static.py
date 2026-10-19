
from pathlib import Path


def test_optimization_tab_uses_worker_thread_and_has_required_controls():
    source = Path("src/gui/optimization_tab.py").read_text(encoding="utf-8")
    assert "class OptimizationWorker" in source
    assert "QThread" in source
    assert "Rozpocznij optymalizację" in source
    assert "Przerwij po bieżącym kandydacie" in source
    assert "Eksportuj CSV" in source
    assert "Eksportuj JSON" in source
    assert "Program Cycle" not in source or "program_cycle_time" in source
