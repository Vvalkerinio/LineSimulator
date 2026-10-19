from dataclasses import (
    dataclass
)


@dataclass
class ManipulatorSeparationResult:

    minimum_distance: float
    manipulator_a: int | None = None
    manipulator_b: int | None = None
    time: float | None = None
    position_a: float | None = None
    position_b: float | None = None
    segment_a_type: str = ""
    segment_b_type: str = ""
    segment_a_start_time: float | None = None
    segment_a_end_time: float | None = None
    segment_b_start_time: float | None = None
    segment_b_end_time: float | None = None
    required_spacing: float = 1.0
    collision: bool = False
    status: str = "OK"


class ManipulatorSeparationReport:

    def analyze(
        self,
        result,
        configuration
    ):
        minimum_spacing = float(
            getattr(
                configuration,
                "minimum_manipulator_spacing",
                1.0
            )
        )

        segments = list(
            getattr(
                result,
                "timeline_segments",
                []
            )
        )

        best = ManipulatorSeparationResult(
            minimum_distance=999999999.0,
            required_spacing=minimum_spacing,
            collision=False,
            status="OK"
        )

        for index_a in range(
            len(
                segments
            )
        ):
            segment_a = (
                segments[
                    index_a
                ]
            )

            for index_b in range(
                index_a
                +
                1,
                len(
                    segments
                )
            ):
                segment_b = (
                    segments[
                        index_b
                    ]
                )

                if (
                    int(
                        segment_a.manipulator_id
                    )
                    ==
                    int(
                        segment_b.manipulator_id
                    )
                ):
                    continue

                if not self._segments_overlap_in_time(
                    segment_a,
                    segment_b
                ):
                    continue

                distance_data = (
                    self._minimum_distance_between_segments(
                        segment_a,
                        segment_b
                    )
                )

                if distance_data is None:
                    continue

                distance = (
                    distance_data[
                        "distance"
                    ]
                )

                if (
                    distance
                    <
                    best.minimum_distance
                ):
                    best = ManipulatorSeparationResult(
                        minimum_distance=(
                            distance
                        ),
                        manipulator_a=(
                            int(
                                segment_a.manipulator_id
                            )
                        ),
                        manipulator_b=(
                            int(
                                segment_b.manipulator_id
                            )
                        ),
                        time=(
                            distance_data[
                                "time"
                            ]
                        ),
                        position_a=(
                            distance_data[
                                "position_a"
                            ]
                        ),
                        position_b=(
                            distance_data[
                                "position_b"
                            ]
                        ),
                        segment_a_type=(
                            str(
                                getattr(
                                    segment_a,
                                    "segment_type",
                                    ""
                                )
                            )
                        ),
                        segment_b_type=(
                            str(
                                getattr(
                                    segment_b,
                                    "segment_type",
                                    ""
                                )
                            )
                        ),
                        segment_a_start_time=(
                            float(
                                segment_a.start_time
                            )
                        ),
                        segment_a_end_time=(
                            float(
                                segment_a.end_time
                            )
                        ),
                        segment_b_start_time=(
                            float(
                                segment_b.start_time
                            )
                        ),
                        segment_b_end_time=(
                            float(
                                segment_b.end_time
                            )
                        ),
                        required_spacing=(
                            minimum_spacing
                        ),
                        collision=(
                            distance
                            <=
                            minimum_spacing
                            +
                            1e-6
                        ),
                        status=(
                            "COLLISION"
                            if distance < minimum_spacing
                            else "OK"
                        )
                    )

        if (
            best.minimum_distance
            ==
            999999999.0
        ):
            best.minimum_distance = 0.0
            best.status = "NO_SEGMENTS"
            best.collision = False

        result.separation_report = (
            best
        )

        return best

    def print_summary(
        self,
        result,
        configuration
    ):
        report = (
            self.analyze(
                result,
                configuration
            )
        )

        print()
        print(
            "="
            *
            60
        )
        print(
            "MANIPULATOR SEPARATION REPORT"
        )
        print(
            "="
            *
            60
        )

        print(
            f"Minimum distance: "
            f"{report.minimum_distance:.2f}"
        )

        if (
            report.manipulator_a is not None
            and
            report.manipulator_b is not None
        ):
            print(
                f"Manipulators: "
                f"M{report.manipulator_a}/M{report.manipulator_b}"
            )

        if report.time is not None:
            print(
                f"Time: "
                f"{report.time:.1f}s"
            )

        if (
            report.position_a is not None
            and
            report.position_b is not None
        ):
            print(
                f"Positions: "
                f"{report.position_a:.2f} / "
                f"{report.position_b:.2f}"
            )

        if (
            report.manipulator_a is not None
            and
            report.manipulator_b is not None
        ):
            print(
                f"Segments: "
                f"M{report.manipulator_a} "
                f"{report.segment_a_type} "
                f"{report.segment_a_start_time:.1f}"
                f".."
                f"{report.segment_a_end_time:.1f} / "
                f"M{report.manipulator_b} "
                f"{report.segment_b_type} "
                f"{report.segment_b_start_time:.1f}"
                f".."
                f"{report.segment_b_end_time:.1f}"
            )

        print(
            f"Required spacing: "
            f"{report.required_spacing:.2f}"
        )
        print(
            "Rule: COLLISION when distance < required spacing"
        )

        print(
            f"STATUS: "
            f"{report.status}"
        )

        print(
            "="
            *
            60
        )

        return report

    def _segments_overlap_in_time(
        self,
        segment_a,
        segment_b
    ):
        return not (
            float(
                segment_a.end_time
            )
            <
            float(
                segment_b.start_time
            )
            or
            float(
                segment_b.end_time
            )
            <
            float(
                segment_a.start_time
            )
        )

    def _position_at(
        self,
        segment,
        time_value
    ):
        start_time = float(
            segment.start_time
        )

        end_time = float(
            segment.end_time
        )

        start_position = float(
            segment.start_position
        )

        end_position = float(
            segment.end_position
        )

        if (
            end_time
            <=
            start_time
        ):
            return (
                end_position
            )

        ratio = (
            float(
                time_value
            )
            -
            start_time
        ) / (
            end_time
            -
            start_time
        )

        ratio = max(
            0.0,
            min(
                1.0,
                ratio
            )
        )

        return (
            start_position
            +
            (
                end_position
                -
                start_position
            )
            *
            ratio
        )

    def _velocity(
        self,
        segment
    ):
        start_time = float(
            segment.start_time
        )

        end_time = float(
            segment.end_time
        )

        if (
            end_time
            <=
            start_time
        ):
            return 0.0

        return (
            float(
                segment.end_position
            )
            -
            float(
                segment.start_position
            )
        ) / (
            end_time
            -
            start_time
        )

    def _minimum_distance_between_segments(
        self,
        segment_a,
        segment_b
    ):
        left = max(
            float(
                segment_a.start_time
            ),
            float(
                segment_b.start_time
            )
        )

        right = min(
            float(
                segment_a.end_time
            ),
            float(
                segment_b.end_time
            )
        )

        if (
            right
            <
            left
        ):
            return None

        check_times = [
            left,
            right
        ]

        velocity_a = (
            self._velocity(
                segment_a
            )
        )

        velocity_b = (
            self._velocity(
                segment_b
            )
        )

        relative_velocity = (
            velocity_a
            -
            velocity_b
        )

        if (
            abs(
                relative_velocity
            )
            >
            1e-9
        ):
            position_a_left = (
                self._position_at(
                    segment_a,
                    left
                )
            )

            position_b_left = (
                self._position_at(
                    segment_b,
                    left
                )
            )

            relative_position_left = (
                position_a_left
                -
                position_b_left
            )

            crossing_time = (
                left
                -
                relative_position_left
                /
                relative_velocity
            )

            if (
                left
                <=
                crossing_time
                <=
                right
            ):
                check_times.append(
                    crossing_time
                )

        #
        # Dodatkowe próbki stabilizują przypadki graniczne:
        # idle + move oraz bardzo krótkie segmenty.
        #
        mid = (
            left
            +
            right
        ) / 2.0

        check_times.append(
            mid
        )

        best_distance = None
        best_time = None
        best_position_a = None
        best_position_b = None

        for time_value in check_times:
            position_a = (
                self._position_at(
                    segment_a,
                    time_value
                )
            )

            position_b = (
                self._position_at(
                    segment_b,
                    time_value
                )
            )

            distance = abs(
                position_a
                -
                position_b
            )

            if (
                best_distance is None
                or
                distance
                <
                best_distance
            ):
                best_distance = (
                    distance
                )
                best_time = (
                    time_value
                )
                best_position_a = (
                    position_a
                )
                best_position_b = (
                    position_b
                )

        return {
            "distance": best_distance,
            "time": best_time,
            "position_a": best_position_a,
            "position_b": best_position_b
        }