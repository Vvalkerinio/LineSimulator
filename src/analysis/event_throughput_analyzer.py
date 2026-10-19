from statistics import mean, median, pstdev

from src.model.event_type import EventType


class EventThroughputAnalyzer:
    """Continuous EventDriven throughput estimates from HANGER_EXIT events."""

    @staticmethod
    def exit_times(result, start=0.0, end=None):
        values = []
        for event in getattr(result, "events", []):
            if event.event_type != EventType.HANGER_EXIT:
                continue
            time_value = float(event.time)
            if time_value < float(start):
                continue
            if end is not None and time_value >= float(end):
                continue
            values.append(time_value)
        return sorted(values)

    def analyze(self, result, start=0.0, end=None):
        if end is None:
            end = float(getattr(result, "final_time", 0.0))
        start, end = float(start), float(end)
        exits = self.exit_times(result, start, end)
        duration = max(0.0, end - start)
        count_rate = len(exits) * 3600.0 / duration if duration > 0 else 0.0
        intervals = [right - left for left, right in zip(exits, exits[1:])
                     if right > left]
        interval_rate = (
            3600.0 / mean(intervals) if intervals else 0.0
        )
        median_rate = (
            3600.0 / median(intervals) if intervals else 0.0
        )
        interval_cv = 0.0
        if len(intervals) >= 2 and mean(intervals) > 0:
            interval_cv = pstdev(intervals) / mean(intervals)
        return {
            "analysis_start": start,
            "analysis_end": end,
            "analysis_duration": duration,
            "exit_count": len(exits),
            "count_rate_per_hour": count_rate,
            "interval_rate_per_hour": interval_rate,
            "median_interval_rate_per_hour": median_rate,
            "mean_exit_interval": mean(intervals) if intervals else None,
            "exit_interval_cv": interval_cv,
            "first_exit": exits[0] if exits else None,
            "last_exit": exits[-1] if exits else None
        }
