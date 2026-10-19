from src.model.event_type import EventType


class ProgramCycleKPI:
    """Calculates ProgramDriven throughput from complete PLC cycles.

    Window throughput remains diagnostic. The release KPI is based on unique
    hanger exits recorded inside complete program-cycle boundaries.
    """

    def calculate(self, result):
        executions = list(getattr(result, "program_word_executions", []))
        if not executions:
            return None

        cycle_numbers = sorted({
            int(execution.cycle_no)
            for execution in executions
        })
        cycle_ranges = []

        for cycle_no in cycle_numbers:
            cycle_executions = [
                execution
                for execution in executions
                if int(execution.cycle_no) == cycle_no
            ]
            if not cycle_executions:
                continue

            cycle_start = min(
                float(execution.start_time)
                for execution in cycle_executions
            )
            cycle_end = max(
                float(execution.end_time)
                for execution in cycle_executions
            )
            if cycle_end <= cycle_start:
                continue

            cycle_ranges.append({
                "cycle_no": cycle_no,
                "start": cycle_start,
                "end": cycle_end,
                "duration": cycle_end - cycle_start
            })

        if not cycle_ranges:
            return None

        exit_events = sorted(
            [
                event
                for event in result.events
                if event.event_type == EventType.HANGER_EXIT
            ],
            key=lambda event: float(event.time)
        )

        last_cycle_no = cycle_ranges[-1]["cycle_no"]
        for cycle_range in cycle_ranges:
            start = cycle_range["start"]
            end = cycle_range["end"]
            include_right_boundary = (
                cycle_range["cycle_no"] == last_cycle_no
            )
            exits = [
                event
                for event in exit_events
                if float(event.time) >= start
                and (
                    float(event.time) < end
                    or (
                        include_right_boundary
                        and float(event.time) <= end
                    )
                )
            ]
            unique_exits = len({
                event.hanger_id
                for event in exits
            })
            cycle_range["exits"] = len(exits)
            cycle_range["unique_exits"] = unique_exits
            cycle_range["throughput"] = (
                unique_exits * 3600.0 / cycle_range["duration"]
            )

        analysis_cycles = (
            cycle_ranges[1:]
            if len(cycle_ranges) > 1
            else cycle_ranges
        )
        total_duration = sum(
            cycle["duration"]
            for cycle in analysis_cycles
        )
        total_unique_exits = sum(
            cycle["unique_exits"]
            for cycle in analysis_cycles
        )
        cycle_count = len(analysis_cycles)
        throughput = (
            total_unique_exits * 3600.0 / total_duration
            if total_duration > 0.0
            else 0.0
        )

        audit = {
            "method": "complete_program_cycles",
            "excluded_warmup_cycles": (
                1 if len(cycle_ranges) > 1 else 0
            ),
            "complete_cycles": cycle_count,
            "cycle_duration": (
                total_duration / cycle_count
                if cycle_count else 0.0
            ),
            "hangers_per_cycle": (
                total_unique_exits / cycle_count
                if cycle_count else 0.0
            ),
            "total_cycle_duration": total_duration,
            "total_unique_exits": total_unique_exits,
            "throughput": throughput,
            "cycles": cycle_ranges
        }
        return audit

    def update_steady_state(self, result, audit):
        """Promotes cycle KPI to the primary ProgramDriven throughput."""
        if audit is None:
            return
        if result.steady_state is None:
            result.steady_state = {}

        analysis_cycle_index = 1 if len(audit["cycles"]) > 1 else 0
        result.steady_state.update({
            "detected": True,
            "steady_state_time": None,
            "throughput": audit["throughput"],
            "reason": "complete_program_cycles",
            "analysis_start": audit["cycles"][analysis_cycle_index]["start"],
            "analysis_end": audit["cycles"][-1]["end"],
            "mean_throughput": audit["throughput"],
            "std_throughput": 0.0,
            "coefficient_of_variation": 0.0,
            "program_cycle_duration": audit["cycle_duration"],
            "hangers_per_cycle": audit["hangers_per_cycle"]
        })
