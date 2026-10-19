from types import SimpleNamespace

from src.optimization import (
    CandidateResult,
    EventDrivenCandidate,
    EventDrivenProgramCandidateBuilder
)


def candidate():
    return EventDrivenCandidate((1, 3, 5, 7), ())


def configuration():
    return SimpleNamespace(
        manipulators=[SimpleNamespace(id=i, position=2 * i - 1)
                      for i in range(1, 5)],
        program_index_addresses={1: 500, 2: 600, 3: 700, 4: 800},
        program_station_offsets={1: 0, 2: 0, 3: 0, 4: 0}
    )


def event_result():
    return SimpleNamespace(
        final_time=1000.0,
        steady_state={"analysis_start": 400.0, "analysis_end": 900.0}
    )


def evaluation(status="VALID", context=True):
    metrics = {}
    if context:
        metrics = {"configuration": configuration(), "result": event_result()}
    return CandidateResult(candidate(), status, (1,), metrics, ())


class Cycle:
    valid = True
    start_time = 500.0
    end_time = 800.0
    manipulator_initial_phase = {1: (1, 0), 2: (3, 0),
                                 3: (5, 0), 4: (7, 0)}
    station_initial_phase = {1: 101, 4: 202}
    messages = []


class Finder:
    captured = []
    def __init__(self, **kwargs): self.kwargs = kwargs
    def find_best(self, **kwargs):
        self.captured.append(kwargs)
        return Cycle()


class Program:
    def __init__(self):
        self.steps = [object()]
        self.max_program_words = 99


class ProgramBuilder:
    captured = []
    def __init__(self, **kwargs):
        self.captured.append(kwargs)
    def build(self):
        return {mid: Program() for mid in (1, 2, 3, 4)}


class Resolution:
    consults = [SimpleNamespace(source_plc_index=1)]
    simulation_result = object()
    stopped_reason = "STABLE"


class Pipeline:
    captured = []
    def __init__(self, **kwargs):
        self.captured.append(kwargs)
    def generate(self): return Resolution()


def builder(**kwargs):
    return EventDrivenProgramCandidateBuilder(
        cycle_finder_factory=Finder,
        program_builder_factory=ProgramBuilder,
        consult_pipeline_factory=Pipeline,
        **kwargs
    )


def test_builds_new_programs_and_new_consults_from_event_result():
    result = builder().build(evaluation())
    assert result.valid
    assert set(result.programs) == {1, 2, 3, 4}
    assert len(result.consults) == 1
    assert result.cycle.start_time == 500.0
    assert Finder.captured[-1] == {"seed_start": 400.0, "seed_end": 900.0}
    assert ProgramBuilder.captured[-1]["cycle_start_time"] == 500.0
    assert Pipeline.captured[-1]["initial_manipulator_positions"] == {
        1: 1, 2: 3, 3: 5, 4: 7
    }
    assert Pipeline.captured[-1]["initial_station_occupancy"] == {
        1: 101, 4: 202
    }


def test_rejected_event_candidate_is_not_built():
    result = builder().build(evaluation(status="REJECTED"))
    assert not result.valid
    assert result.errors == ["EVENT_CANDIDATE_NOT_VALID"]


def test_missing_context_is_rejected():
    result = builder().build(evaluation(context=False))
    assert not result.valid
    assert result.errors == ["EVENT_RESULT_CONTEXT_MISSING"]


def test_invalid_cycle_is_rejected_before_program_builder():
    class InvalidFinder(Finder):
        def find_best(self, **kwargs):
            cycle = Cycle()
            cycle.valid = False
            cycle.messages = ["not closed"]
            return cycle
    current = EventDrivenProgramCandidateBuilder(
        cycle_finder_factory=InvalidFinder,
        program_builder_factory=lambda **kwargs: (_ for _ in ()).throw(
            AssertionError("must not build")
        ),
        consult_pipeline_factory=Pipeline
    ).build(evaluation())
    assert not current.valid
    assert current.errors == ["EVENT_NO_VALID_CLOSED_CYCLE"]
    assert current.notes == ["not closed"]


def test_program_word_limit_is_checked_before_consult_generation():
    class OversizedProgram(Program):
        def __init__(self):
            self.steps = [object()] * 34
            self.max_program_words = 99
    class OversizedBuilder(ProgramBuilder):
        def build(self):
            return {mid: OversizedProgram() for mid in (1, 2, 3, 4)}
    current = EventDrivenProgramCandidateBuilder(
        cycle_finder_factory=Finder,
        program_builder_factory=OversizedBuilder,
        consult_pipeline_factory=lambda **kwargs: (_ for _ in ()).throw(
            AssertionError("must not resolve consults")
        )
    ).build(evaluation())
    assert not current.valid
    assert all(error.startswith("PROGRAM_WORD_LIMIT_M")
               for error in current.errors)
