from statistics import mean, pstdev

from src.model.event_type import (
    EventType
)


class SteadyStateDetector:

    def __init__(
        self,
        tolerance: float = 0.05,
        required_windows: int = 3,
        cv_tolerance: float = 0.35
    ):
        self.tolerance = (
            tolerance
        )

        self.required_windows = (
            required_windows
        )

        self.cv_tolerance = (
            cv_tolerance
        )

    def completion_times(
        self,
        result,
        analysis_start: float = 0.0,
        analysis_end: float | None = None
    ):

        values = []

        for event in (
            getattr(result, "events", [])
        ):

            if (
                event.event_type
                != EventType.HANGER_EXIT
            ):
                continue

            if (
                event.time
                < analysis_start
            ):
                continue

            if (
                analysis_end is not None
                and
                event.time
                >= analysis_end
            ):
                continue

            values.append(
                event.time
            )

        return sorted(
            values
        )

    def build_windows(
        self,
        result,
        window_size: float,
        analysis_start: float = 0.0,
        analysis_end: float | None = None
    ):

        if window_size <= 0:
            return []

        if analysis_end is None:

            analysis_end = (
                result.final_time
            )

        if (
            analysis_end
            <= analysis_start
        ):
            return []

        completions = (
            self.completion_times(
                result,
                analysis_start=
                    analysis_start,
                analysis_end=
                    analysis_end
            )
        )

        windows = []

        current = (
            analysis_start
        )

        while (
            current + window_size
            <= analysis_end
        ):

            window_end = (
                current
                + window_size
            )

            count = sum(
                1
                for time_value
                in completions
                if (
                    current
                    <= time_value
                    < window_end
                )
            )

            throughput = (
                count
                * 3600.0
                / window_size
            )

            windows.append(
                {
                    "start":
                        current,

                    "end":
                        window_end,

                    "completed":
                        count,

                    "throughput":
                        throughput
                }
            )

            current = (
                window_end
            )

        return windows

    def _window_to_window_detection(
        self,
        windows
    ):

        stable_count = 0

        previous_throughput = None

        for window in (
            windows
        ):

            throughput = (
                window[
                    "throughput"
                ]
            )

            if previous_throughput is None:

                previous_throughput = (
                    throughput
                )

                continue

            if previous_throughput == 0:

                variation = (
                    0.0
                    if throughput == 0
                    else 1.0
                )

            else:

                variation = (
                    abs(
                        throughput
                        - previous_throughput
                    )
                    / previous_throughput
                )

            window[
                "variation"
            ] = (
                variation
            )

            if (
                variation
                <= self.tolerance
            ):

                stable_count += 1

            else:

                stable_count = 0

            previous_throughput = (
                throughput
            )

            if (
                stable_count
                >= self.required_windows
            ):

                return {
                    "detected":
                        True,

                    "reason":
                        "stable_throughput",

                    "steady_state_time":
                        window[
                            "start"
                        ],

                    "throughput":
                        throughput
                }

        return None

    def _periodic_detection(
        self,
        windows
    ):

        values = [
            window[
                "throughput"
            ]
            for window
            in windows
        ]

        positive_values = [
            value
            for value
            in values
            if value > 0
        ]

        if (
            len(positive_values)
            < self.required_windows
        ):

            return None

        mean_value = (
            mean(
                positive_values
            )
        )

        if mean_value <= 0:

            return None

        std_value = (
            pstdev(
                positive_values
            )
        )

        cv_value = (
            std_value
            / mean_value
        )

        if (
            cv_value
            <= self.cv_tolerance
        ):

            return {
                "detected":
                    True,

                "reason":
                    "stable_periodic_throughput",

                "steady_state_time":
                    windows[
                        0
                    ][
                        "start"
                    ],

                "throughput":
                    mean_value,

                "mean_throughput":
                    mean_value,

                "std_throughput":
                    std_value,

                "coefficient_of_variation":
                    cv_value
            }

        return {
            "detected":
                False,

            "reason":
                "periodic_variation_too_high",

            "steady_state_time":
                None,

            "throughput":
                None,

            "mean_throughput":
                mean_value,

            "std_throughput":
                std_value,

            "coefficient_of_variation":
                cv_value
        }

    def detect(
        self,
        result,
        window_size: float = 600.0,
        analysis_start: float = 0.0,
        analysis_end: float | None = None
    ):

        windows = (
            self.build_windows(
                result,
                window_size=
                    window_size,
                analysis_start=
                    analysis_start,
                analysis_end=
                    analysis_end
            )
        )

        if (
            len(windows)
            < self.required_windows
            + 1
        ):

            return {
                "detected":
                    False,

                "reason":
                    "not_enough_windows",

                "steady_state_time":
                    None,

                "throughput":
                    None,

                "analysis_start":
                    analysis_start,

                "analysis_end":
                    analysis_end,

                "windows":
                    windows,

                "mean_throughput":
                    None,

                "std_throughput":
                    None,

                "coefficient_of_variation":
                    None
            }

        all_zero = all(
            float(window.get("throughput", 0.0)) == 0.0
            for window in windows
        )
        blocked_flow = bool(
            getattr(result, "deferred_transports", [])
            or getattr(result, "deadlocks", [])
        )
        if all_zero and blocked_flow:
            return {
                "detected": False,
                "reason": "stable_zero_deadlock",
                "steady_state_time": None,
                "throughput": 0.0,
                "analysis_start": analysis_start,
                "analysis_end": analysis_end,
                "windows": windows,
                "mean_throughput": 0.0,
                "std_throughput": 0.0,
                "coefficient_of_variation": None
            }

        classic = (
            self._window_to_window_detection(
                windows
            )
        )

        periodic = (
            self._periodic_detection(
                windows
            )
        )

        if (
            classic is not None
            and
            classic.get(
                "detected",
                False
            )
        ):

            values = [
                window[
                    "throughput"
                ]
                for window
                in windows
                if window[
                    "throughput"
                ] > 0
            ]

            mean_value = (
                mean(values)
                if values
                else 0.0
            )

            std_value = (
                pstdev(values)
                if len(values) > 1
                else 0.0
            )

            cv_value = (
                std_value / mean_value
                if mean_value > 0
                else None
            )

            classic.update(
                {
                    "analysis_start":
                        analysis_start,

                    "analysis_end":
                        analysis_end,

                    "windows":
                        windows,

                    "mean_throughput":
                        mean_value,

                    "std_throughput":
                        std_value,

                    "coefficient_of_variation":
                        cv_value
                }
            )

            return classic

        if (
            periodic is not None
            and
            periodic.get(
                "detected",
                False
            )
        ):

            periodic.update(
                {
                    "analysis_start":
                        analysis_start,

                    "analysis_end":
                        analysis_end,

                    "windows":
                        windows
                }
            )

            return periodic

        if periodic is not None:

            periodic.update(
                {
                    "analysis_start":
                        analysis_start,

                    "analysis_end":
                        analysis_end,

                    "windows":
                        windows
                }
            )

            return periodic

        return {
            "detected":
                False,

            "reason":
                "unstable_throughput",

            "steady_state_time":
                None,

            "throughput":
                None,

            "analysis_start":
                analysis_start,

            "analysis_end":
                analysis_end,

            "windows":
                windows,

            "mean_throughput":
                None,

            "std_throughput":
                None,

            "coefficient_of_variation":
                None
        }