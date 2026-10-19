class ProgramConsultSynchronizer:
    """Indexes PLC consults, detects blocking conditions and records waits."""

    def __init__(
        self,
        consults,
        completed_target_resolver,
        target_time_resolver,
        recheck_interval=0.1
    ):
        self.consults = list(consults or [])
        self.completed_target_resolver = completed_target_resolver
        self.target_time_resolver = target_time_resolver
        self.recheck_interval = float(recheck_interval)
        self._by_source = {}
        for consult_no, consult in enumerate(self.consults, start=1):
            key = (
                int(consult.source_manipulator_id),
                int(consult.source_plc_index)
            )
            self._by_source.setdefault(key, []).append((consult_no, consult))

    def blocking_consult(self, runtime, runtimes):
        key = (
            int(runtime.manipulator_id),
            int(runtime.current_plc_index)
        )
        for consult_no, consult in self._by_source.get(key, []):
            completed = self.completed_target_resolver(
                runtimes=runtimes,
                target_manipulator_id=int(consult.target_manipulator_id),
                target_plc_index=int(consult.target_plc_index)
            )
            if not completed:
                return consult_no, consult
        return None

    @staticmethod
    def label(consult):
        return (
            f"M{int(consult.target_manipulator_id)}:"
            f"{int(consult.target_plc_index)}"
        )

    def _wait_key(self, runtime):
        return (
            int(runtime.manipulator_id),
            int(runtime.cycle_no),
            int(runtime.current_plc_index)
        )

    def close_wait(self, state, runtime, end_time=None):
        active = state.setdefault("active_consult_waits", {})
        record = active.pop(self._wait_key(runtime), None)
        if record is None:
            return None
        record["end_time"] = float(
            runtime.available_time if end_time is None else end_time
        )
        record["duration"] = max(
            0.0,
            record["end_time"] - record["start_time"]
        )
        state.setdefault("consult_waits", []).append(record)
        return record

    def apply_block(self, state, runtime, runtimes, consult_no, consult):
        wait_start = float(runtime.available_time)
        key = self._wait_key(runtime)
        active = state.setdefault("active_consult_waits", {})
        if key not in active:
            active[key] = {
                "consult_no": int(consult_no),
                "manipulator_id": int(runtime.manipulator_id),
                "cycle_no": int(runtime.cycle_no),
                "source_plc_index": int(runtime.current_plc_index),
                "target_manipulator_id": int(consult.target_manipulator_id),
                "target_plc_index": int(consult.target_plc_index),
                "label": self.label(consult),
                "position": float(runtime.current_position),
                "start_time": wait_start,
                "end_time": wait_start,
                "duration": 0.0
            }

        target_runtime = runtimes.get(int(consult.target_manipulator_id))
        target_time = self.target_time_resolver(
            runtimes,
            int(consult.target_manipulator_id),
            int(consult.target_plc_index)
        )
        if target_time is None:
            if target_runtime is not None:
                runtime.available_time = max(
                    runtime.available_time,
                    target_runtime.available_time + self.recheck_interval
                )
            else:
                runtime.available_time += self.recheck_interval
        else:
            runtime.available_time = max(runtime.available_time, target_time)

        active[key]["end_time"] = float(runtime.available_time)
        active[key]["duration"] = max(
            0.0,
            active[key]["end_time"] - active[key]["start_time"]
        )
        return runtime.available_time

    def evaluate(self, state, runtime, runtimes):
        blocked = self.blocking_consult(runtime, runtimes)
        if blocked is None:
            self.close_wait(state, runtime)
            return None
        consult_no, consult = blocked
        self.apply_block(
            state, runtime, runtimes, consult_no, consult
        )
        return consult

    def finalize(self, state, end_time):
        active = state.setdefault("active_consult_waits", {})
        for record in list(active.values()):
            record["end_time"] = max(float(end_time), record["start_time"])
            record["duration"] = record["end_time"] - record["start_time"]
            state.setdefault("consult_waits", []).append(record)
        active.clear()
