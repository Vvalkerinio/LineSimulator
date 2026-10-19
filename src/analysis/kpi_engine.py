from src.model.kpi_result import KPIResult
from src.analysis.event_throughput_analyzer import EventThroughputAnalyzer


class KPIEngine:
    """Unified KPI calculation for ProgramDriven and EventDriven results."""

    def calculate(self, simulation_result, pieces_per_transport=None) -> KPIResult:
        simulation_time = float(simulation_result.final_time)
        steady = getattr(simulation_result, "steady_state", None) or {}
        start = steady.get(
            "analysis_start", steady.get("steady_state_time", 0.0)
        )
        end = steady.get("analysis_end", simulation_time)
        analysis = EventThroughputAnalyzer().analyze(
            simulation_result, start or 0.0, end
        )
        interval_rate = float(analysis["interval_rate_per_hour"])
        window_rate = float(
            steady.get("throughput", steady.get("mean_throughput", 0.0))
            or 0.0
        )
        legacy_rate = (
            float(simulation_result.completed_transports) * 3600.0
            / simulation_time if simulation_time > 0.0 else 0.0
        )
        program_cycle = getattr(simulation_result, "program_cycle_kpi", None) or {}
        program_cycle_rate = float(program_cycle.get("throughput", 0.0) or 0.0)
        # Physical exit intervals are authoritative whenever they exist. A
        # legacy ProgramDriven result without HANGER_EXIT records keeps its
        # cycle throughput as a compatibility fallback.
        transports_per_hour = (
            interval_rate or window_rate or program_cycle_rate or legacy_rate
        )
        pieces = int(
            pieces_per_transport
            if pieces_per_transport is not None
            else getattr(simulation_result, "pieces_per_transport", 7)
        )
        pieces = max(1, pieces)
        average_cycle_time = analysis.get("mean_exit_interval")
        steady["windowed_throughput"] = window_rate
        steady["interval_throughput"] = interval_rate
        steady["precise_throughput"] = transports_per_hour
        steady["throughput_exit_count"] = analysis["exit_count"]
        steady["mean_exit_interval"] = average_cycle_time
        steady["exit_interval_cv"] = analysis["exit_interval_cv"]
        steady["transports_per_hour"] = transports_per_hour
        steady["pieces_per_transport"] = pieces
        steady["parts_per_hour"] = transports_per_hour * pieces
        simulation_result.steady_state = steady
        simulation_result.pieces_per_transport = pieces
        simulation_result.transports_per_hour = transports_per_hour
        simulation_result.parts_per_hour = transports_per_hour * pieces
        simulation_result.average_cycle_time = average_cycle_time
        return KPIResult(
            simulation_time=simulation_time,
            processed_events=simulation_result.processed_events,
            scheduled_transports=simulation_result.scheduled_transports,
            completed_transports=simulation_result.completed_transports,
            transports_per_hour=transports_per_hour,
            pieces_per_transport=pieces,
            parts_per_hour=transports_per_hour * pieces,
            average_cycle_time=average_cycle_time,
        )
