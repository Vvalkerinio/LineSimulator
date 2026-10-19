from src.analysis.text_table_utils import format_text_table
class ManipulatorUtilizationReport:

    def _duration(
        self,
        segment
    ):
        return max(
            0.0,
            segment.end_time
            -
            segment.start_time
        )

    def _known_manipulator_ids(
        self,
        result,
        config=None
    ):
        ids = set()

        if config is not None:
            for manipulator in getattr(
                config,
                "manipulators",
                []
            ):
                ids.add(
                    manipulator.id
                )

        for segment in getattr(
            result,
            "timeline_segments",
            []
        ):
            ids.add(
                segment.manipulator_id
            )

        for task in getattr(
            result,
            "manipulator_tasks",
            []
        ):
            ids.add(
                task.manipulator_id
            )

        return sorted(
            ids
        )

    def _task_counts(
        self,
        result
    ):
        counts = {}

        for task in getattr(
            result,
            "manipulator_tasks",
            []
        ):
            counts[
                task.manipulator_id
            ] = (
                counts.get(
                    task.manipulator_id,
                    0
                )
                + 1
            )

        return counts

    def _timeline_summary(
        self,
        result,
        manipulator_ids
    ):
        summary = {}

        for manipulator_id in manipulator_ids:
            summary[
                manipulator_id
            ] = {
                "busy_time": 0.0,
                "idle_time": 0.0,
                "empty_move_time": 0.0,
                "loaded_move_time": 0.0,
                "return_move_time": 0.0,
                "other_move_time": 0.0
            }

        for segment in getattr(
            result,
            "timeline_segments",
            []
        ):
            duration = (
                self._duration(
                    segment
                )
            )

            manipulator_id = (
                segment.manipulator_id
            )

            if manipulator_id not in summary:
                summary[
                    manipulator_id
                ] = {
                    "busy_time": 0.0,
                    "idle_time": 0.0,
                    "empty_move_time": 0.0,
                    "loaded_move_time": 0.0,
                    "return_move_time": 0.0,
                    "other_move_time": 0.0
                }

            segment_type = getattr(
                segment,
                "segment_type",
                ""
            )

            if segment_type == "idle":
                summary[
                    manipulator_id
                ][
                    "idle_time"
                ] += duration

                continue

            summary[
                manipulator_id
            ][
                "busy_time"
            ] += duration

            if segment_type == "empty_move":
                summary[
                    manipulator_id
                ][
                    "empty_move_time"
                ] += duration

            elif segment_type == "loaded_move":
                summary[
                    manipulator_id
                ][
                    "loaded_move_time"
                ] += duration

            elif segment_type == "return_move":
                summary[
                    manipulator_id
                ][
                    "return_move_time"
                ] += duration

            else:
                summary[
                    manipulator_id
                ][
                    "other_move_time"
                ] += duration

        return summary

    def print_summary(
        self,
        result,
        config=None
    ):
        manipulator_ids = (
            self._known_manipulator_ids(
                result,
                config
            )
        )

        if not manipulator_ids:
            return

        final_time = getattr(
            result,
            "final_time",
            0.0
        )

        if final_time <= 0:
            max_segment_time = 0.0

            for segment in getattr(
                result,
                "timeline_segments",
                []
            ):
                max_segment_time = max(
                    max_segment_time,
                    segment.end_time
                )

            final_time = max_segment_time

        if final_time <= 0:
            return

        task_counts = (
            self._task_counts(
                result
            )
        )

        timeline = (
            self._timeline_summary(
                result,
                manipulator_ids
            )
        )

        task_counts = self._task_counts(result)
        timeline = self._timeline_summary(result, manipulator_ids)
        rows = []
        total_busy = 0.0
        for manipulator_id in manipulator_ids:
            data = timeline.get(manipulator_id, {})
            busy_time = data.get("busy_time", 0.0)
            idle_time = data.get(
                "idle_time", max(0.0, final_time - busy_time)
            )
            utilization = busy_time / final_time * 100.0
            total_busy += busy_time
            rows.append([
                f"M{manipulator_id}",
                str(task_counts.get(manipulator_id, 0)),
                f"{busy_time:.1f}",
                f"{idle_time:.1f}",
                f"{utilization:.2f}",
                f"{data.get('empty_move_time', 0.0):.1f}",
                f"{data.get('loaded_move_time', 0.0):.1f}",
                f"{data.get('return_move_time', 0.0):.1f}",
            ])
        average_utilization = (
            total_busy / len(manipulator_ids) / final_time * 100.0
        )
        print()
        print("=" * 92)
        print("MANIPULATOR UTILIZATION REPORT")
        print("=" * 92)
        print(f"Simulation time : {final_time:.1f}s")
        print()
        print(format_text_table(
            ["ID", "Tasks", "Busy[s]", "Idle[s]", "Util[%]",
             "Empty[s]", "Loaded[s]", "Return[s]"],
            rows,
            ["left", "right", "right", "right", "right",
             "right", "right", "right"]
        ))
        print()
        print(f"Average utilization : {average_utilization:.2f}%")
        print("=" * 92)
        print(
            "MANIPULATOR UTILIZATION REPORT"
        )
        print(
            "=" * 60
        )

        print(
            f"Simulation time : {final_time:.1f}s"
        )

        print()
        print(
            "ID   Tasks   Busy[s]   Idle[s]   Util[%]   "
            "Empty[s]   Loaded[s]   Return[s]"
        )

        total_busy = 0.0

        for manipulator_id in manipulator_ids:
            data = timeline.get(
                manipulator_id,
                {}
            )

            busy_time = (
                data.get(
                    "busy_time",
                    0.0
                )
            )

            idle_time = (
                data.get(
                    "idle_time",
                    max(
                        0.0,
                        final_time
                        -
                        busy_time
                    )
                )
            )

            utilization = (
                busy_time
                / final_time
                * 100.0
            )

            total_busy += busy_time

            print(
                f"M{manipulator_id:<3} "
                f"{task_counts.get(manipulator_id, 0):<7} "
                f"{busy_time:>8.1f} "
                f"{idle_time:>8.1f} "
                f"{utilization:>8.2f} "
                f"{data.get('empty_move_time', 0.0):>9.1f} "
                f"{data.get('loaded_move_time', 0.0):>10.1f} "
                f"{data.get('return_move_time', 0.0):>10.1f}"
            )

        average_utilization = (
            total_busy
            /
            (
                final_time
                *
                len(
                    manipulator_ids
                )
            )
            *
            100.0
        )

        print()
        print(
            f"Average utilization : "
            f"{average_utilization:.2f}%"
        )

        print(
            "=" * 60
        )