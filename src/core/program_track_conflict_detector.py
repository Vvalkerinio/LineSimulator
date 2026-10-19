class ProgramTrackConflictDetector:
    """Detects spacing conflicts between linear manipulator timeline segments."""

    def __init__(
        self,
        configuration,
        distance_epsilon=1e-6
    ):
        self.configuration = configuration
        self.distance_epsilon = float(distance_epsilon)

    def minimum_spacing(self):
        return float(getattr(
            self.configuration,
            "minimum_manipulator_spacing",
            1.0
        ))

    @staticmethod
    def position_on_segment(
        start_time,
        end_time,
        start_position,
        end_position,
        time_value
    ):
        start_time = float(start_time)
        end_time = float(end_time)
        start_position = float(start_position)
        end_position = float(end_position)
        time_value = float(time_value)

        if end_time <= start_time:
            return end_position

        ratio = (time_value - start_time) / (end_time - start_time)
        ratio = max(0.0, min(1.0, ratio))
        return start_position + (end_position - start_position) * ratio

    def minimum_distance(
        self,
        a_start_time,
        a_end_time,
        a_start_position,
        a_end_position,
        b_start_time,
        b_end_time,
        b_start_position,
        b_end_position
    ):
        left = max(float(a_start_time), float(b_start_time))
        right = min(float(a_end_time), float(b_end_time))
        if right < left:
            return None

        check_times = [left, right]
        a_duration = float(a_end_time) - float(a_start_time)
        b_duration = float(b_end_time) - float(b_start_time)
        a_velocity = (
            (float(a_end_position) - float(a_start_position)) / a_duration
            if a_duration > 0.0 else 0.0
        )
        b_velocity = (
            (float(b_end_position) - float(b_start_position)) / b_duration
            if b_duration > 0.0 else 0.0
        )
        relative_velocity = a_velocity - b_velocity

        if abs(relative_velocity) > 1e-9:
            relative_position = (
                self.position_on_segment(
                    a_start_time, a_end_time,
                    a_start_position, a_end_position,
                    left
                )
                -
                self.position_on_segment(
                    b_start_time, b_end_time,
                    b_start_position, b_end_position,
                    left
                )
            )
            crossing_time = left - relative_position / relative_velocity
            if left <= crossing_time <= right:
                check_times.append(crossing_time)

        return min(
            abs(
                self.position_on_segment(
                    a_start_time, a_end_time,
                    a_start_position, a_end_position,
                    time_value
                )
                -
                self.position_on_segment(
                    b_start_time, b_end_time,
                    b_start_position, b_end_position,
                    time_value
                )
            )
            for time_value in check_times
        )

    def find_conflict(
        self,
        result,
        runtime,
        start_time,
        end_time,
        source_position,
        target_position
    ):
        minimum_spacing = self.minimum_spacing()
        conflict = None

        for segment in getattr(result, "timeline_segments", []):
            if int(segment.manipulator_id) == int(runtime.manipulator_id):
                continue
            if (
                float(segment.end_time) < float(start_time)
                or float(segment.start_time) > float(end_time)
            ):
                continue

            # Szybki test obwiedni przestrzennej. Jeżeli całe zakresy
            # pozycji są dalej od siebie niż wymagany odstęp, dokładne
            # obliczenie przecięcia dwóch funkcji liniowych jest zbędne.
            move_min = min(float(source_position), float(target_position))
            move_max = max(float(source_position), float(target_position))
            segment_min = min(
                float(segment.start_position),
                float(segment.end_position)
            )
            segment_max = max(
                float(segment.start_position),
                float(segment.end_position)
            )
            if (
                move_max + minimum_spacing < segment_min
                or segment_max + minimum_spacing < move_min
            ):
                continue

            distance = self.minimum_distance(
                a_start_time=start_time,
                a_end_time=end_time,
                a_start_position=source_position,
                a_end_position=target_position,
                b_start_time=segment.start_time,
                b_end_time=segment.end_time,
                b_start_position=segment.start_position,
                b_end_position=segment.end_position
            )
            if distance is None:
                continue

            if distance <= minimum_spacing + self.distance_epsilon:
                conflict_end_time = float(segment.end_time)
                if (
                    conflict is None
                    or conflict_end_time > conflict["conflict_end_time"]
                ):
                    conflict = {
                        "other_manipulator_id": segment.manipulator_id,
                        "other_start_time": float(segment.start_time),
                        "other_end_time": float(segment.end_time),
                        "other_start_position": float(segment.start_position),
                        "other_end_position": float(segment.end_position),
                        "distance": distance,
                        "minimum_spacing": minimum_spacing,
                        "conflict_end_time": conflict_end_time
                    }

        return conflict
