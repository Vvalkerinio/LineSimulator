from src.analysis.kpi_engine import (
    KPIEngine
)

from src.model.simulation_result import (
    SimulationResult
)


def test_kpi_calculation():

    result = SimulationResult()

    result.final_time = 1800

    result.processed_events = 20

    result.scheduled_transports = 10

    result.completed_transports = 10

    kpi = KPIEngine().calculate(
        result
    )

    assert (
        kpi.transports_per_hour
        == 20
    )

    assert (
        kpi.completed_transports
        == 10
    )