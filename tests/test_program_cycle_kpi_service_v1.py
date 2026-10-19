from src.analysis.program_cycle_kpi import ProgramCycleKPI
from src.model.simulation_result import SimulationResult


def test_program_cycle_kpi_returns_none_without_executions():
    assert ProgramCycleKPI().calculate(SimulationResult()) is None


def test_update_steady_state_is_noop_without_audit():
    result = SimulationResult()
    result.steady_state = {"reason": "existing"}
    ProgramCycleKPI().update_steady_state(result, None)
    assert result.steady_state == {"reason": "existing"}
