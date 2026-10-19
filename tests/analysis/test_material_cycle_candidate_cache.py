from types import SimpleNamespace

from src.analysis.material_cycle_window_finder import MaterialCycleWindowFinder


def test_candidate_cache_avoids_duplicate_cpu_work_and_isolates_messages():
    finder = MaterialCycleWindowFinder(SimpleNamespace(stations=[]), SimpleNamespace())
    calls = []
    candidate = SimpleNamespace(messages=["base"])
    def build(start, end, seed_start, seed_duration):
        calls.append((start, end, seed_start, seed_duration))
        return candidate
    finder._candidate_uncached = build
    first = finder._candidate(10, 20, 10, 10)
    first.messages.append("caller-only")
    second = finder._candidate(10.0, 20.0, 10.0, 10.0)
    assert len(calls) == 1
    assert second.messages == ["base"]
    assert finder.candidate_cache_stats == {"hits": 1, "misses": 1, "size": 1}
