from copy import deepcopy
from dataclasses import dataclass, field

from src.model.manipulator_program_step import ManipulatorProgramStep
from src.optimization.optimization_constraints import OptimizationConstraints


@dataclass
class ProgramTransformationResult:
    programs: dict
    consults: list
    notes: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    inserted_steps: int = 0

    @property
    def valid(self):
        return not self.errors


class ProgramCandidateTransformer:
    """Transform a PLC program for one optimization candidate.

    The transformer is deterministic and never mutates the source programs or
    consults. It may:
    - move the explicit CYCLE_START_HOLD to the candidate start position,
    - redirect existing empty parking steps to candidate parking positions,
    - insert one consult preposition step before a protected operation,
    - append an explicit empty return to the cycle start position,
    - remap all consult PLC indexes after inserted steps.
    """

    ACTION_PICKUP = 1
    ACTION_DROP = 2
    WORDS_PER_STEP = 3
    SEGMENT_EMPTY_PARKING = "empty_parking"

    def __init__(self, configuration, path_validator=None):
        self.configuration = configuration
        self.path_validator = path_validator or (
            lambda manipulator_id, source, target: True
        )
        self.station_map = {
            int(station.id): station
            for station in getattr(configuration, "stations", [])
        }
        self.manipulator_map = {
            int(item.id): item
            for item in getattr(configuration, "manipulators", [])
        }
        self.constraints = OptimizationConstraints(
            getattr(configuration, "minimum_manipulator_spacing", 2.0)
        )

    @staticmethod
    def _consult_value(consult, name, default=None):
        return getattr(consult, name, default)

    @staticmethod
    def _set_consult_value(consult, name, value):
        if hasattr(consult, name):
            setattr(consult, name, value)

    @staticmethod
    def _plc_index_to_step_index(plc_index):
        value = max(1, int(plc_index))
        return (value - 1) // ProgramCandidateTransformer.WORDS_PER_STEP

    @staticmethod
    def _step_index_to_plc_index(step_index):
        return step_index * ProgramCandidateTransformer.WORDS_PER_STEP + 1

    @staticmethod
    def _station_name(station_map, station_id):
        station = station_map.get(int(station_id))
        return getattr(station, "name", f"ST{station_id}")

    @staticmethod
    def _plc_station_value(program, station_id):
        return int(station_id) - int(program.station_offset) + int(
            program.station_id_shift
        )

    def _parking_step(self, program, station_id, status, command_name,
                      cycle_time=0.0):
        station_id = int(station_id)
        return ManipulatorProgramStep(
            manipulator_id=int(program.manipulator_id),
            step_no=0,
            cycle_time_start=float(cycle_time),
            cycle_time_end=float(cycle_time),
            station_id=station_id,
            plc_station_value=self._plc_station_value(program, station_id),
            action=self.ACTION_DROP,
            wait_time_01s=0,
            command_name=command_name,
            station_name=self._station_name(self.station_map, station_id),
            source_station=station_id,
            target_station=station_id,
            source_name=self._station_name(self.station_map, station_id),
            target_name=self._station_name(self.station_map, station_id),
            hanger_id=None,
            segment_type=self.SEGMENT_EMPTY_PARKING,
            status=status
        )

    def _validate_candidate(self, candidate):
        errors = []
        manipulators = list(self.manipulator_map.values())
        for label, positions in (
            ("START", candidate.start_positions),
            ("PARKING", candidate.parking_positions)
        ):
            for violation in self.constraints.validate_positions(
                positions, manipulators
            ):
                errors.append(f"{label}_{violation.code}: {violation.message}")
        for manipulator_id, position in enumerate(
            candidate.parking_positions, start=1
        ):
            if int(position) not in self.station_map:
                errors.append(
                    f"PARKING_STATION_MISSING: M{manipulator_id} ST{position}"
                )
        return errors

    def _validate_parking_bath(self, candidate):
        errors = []
        positions = tuple(candidate.parking_positions)
        for manipulator_id, position in enumerate(positions, start=1):
            station = self.station_map.get(int(position))
            if station is None or not bool(
                getattr(station, "is_process_bath", True)
            ):
                continue
            manipulator = self.manipulator_map[manipulator_id]
            legal_non_process = []
            for alternative in range(
                int(manipulator.work_zone_start),
                int(manipulator.work_zone_end) + 1
            ):
                target = self.station_map.get(alternative)
                if target is None or bool(
                    getattr(target, "is_process_bath", True)
                ):
                    continue
                if not self.constraints.is_legal_position(
                    manipulator_id, alternative, positions
                ):
                    continue
                if self.path_validator(manipulator_id, position, alternative):
                    legal_non_process.append(alternative)
            if legal_non_process:
                errors.append(
                    f"PROCESS_BATH_PARKING_NOT_FORCED: M{manipulator_id} "
                    f"ST{position}; legal={legal_non_process}"
                )
        return errors

    @staticmethod
    def _is_start_hold(step):
        return str(getattr(step, "status", "")) == "CYCLE_START_HOLD"

    @staticmethod
    def _is_empty_parking(step):
        return str(getattr(step, "segment_type", "")) == "empty_parking"

    def _set_step_station(self, program, step, station_id):
        station_id = int(station_id)
        name = self._station_name(self.station_map, station_id)
        step.station_id = station_id
        step.plc_station_value = self._plc_station_value(program, station_id)
        step.station_name = name
        step.source_station = station_id
        step.target_station = station_id
        step.source_name = name
        step.target_name = name

    @staticmethod
    def _renumber(program):
        for step_no, step in enumerate(program.steps, start=1):
            step.step_no = step_no
            step.manipulator_id = int(program.manipulator_id)

    @staticmethod
    def _consult_source_key(consult):
        return (
            int(getattr(consult, "source_manipulator_id")),
            int(getattr(consult, "source_plc_index"))
        )

    def _insertion_points(self, consults):
        result = {}
        for consult in consults:
            manipulator_id, plc_index = self._consult_source_key(consult)
            result.setdefault(manipulator_id, set()).add(
                self._plc_index_to_step_index(plc_index)
            )
        return result

    @staticmethod
    def _remap_plc_index(old_plc_index, inserted_before):
        old_step_index = ProgramCandidateTransformer._plc_index_to_step_index(
            old_plc_index
        )
        shift = sum(1 for point in inserted_before if point <= old_step_index)
        return int(old_plc_index) + shift * ProgramCandidateTransformer.WORDS_PER_STEP

    @staticmethod
    def _step_signature(step):
        if step is None:
            return None
        return (
            int(getattr(step, "station_id", -1)),
            int(getattr(step, "action", -1)),
            str(getattr(step, "command_name", "")),
            str(getattr(step, "segment_type", "")),
            str(getattr(step, "status", ""))
        )

    def _consult_binding_snapshot(self, programs, consults):
        snapshots = []
        for number, consult in enumerate(consults, start=1):
            source_mid = int(consult.source_manipulator_id)
            target_mid = int(consult.target_manipulator_id)
            source_index = int(consult.source_plc_index)
            target_index = int(consult.target_plc_index)
            source_program = programs.get(source_mid)
            target_program = programs.get(target_mid)
            source_step_index = self._plc_index_to_step_index(source_index)
            target_step_index = self._plc_index_to_step_index(target_index)
            source_step = (
                source_program.steps[source_step_index]
                if source_program is not None
                and 0 <= source_step_index < len(source_program.steps)
                else None
            )
            target_step = (
                target_program.steps[target_step_index]
                if target_program is not None
                and 0 <= target_step_index < len(target_program.steps)
                else None
            )
            snapshots.append({
                "number": number,
                "source_mid": source_mid,
                "target_mid": target_mid,
                "source_index": source_index,
                "target_index": target_index,
                "source_signature": self._step_signature(source_step),
                "target_signature": self._step_signature(target_step)
            })
        return snapshots

    def _audit_consult_bindings(self, programs, consults, snapshots):
        errors = []
        remap_audit = []
        for consult, before in zip(consults, snapshots):
            source_mid = int(consult.source_manipulator_id)
            target_mid = int(consult.target_manipulator_id)
            source_index = int(consult.source_plc_index)
            target_index = int(consult.target_plc_index)
            source_program = programs.get(source_mid)
            target_program = programs.get(target_mid)
            source_step_index = self._plc_index_to_step_index(source_index)
            target_step_index = self._plc_index_to_step_index(target_index)
            source_step = (
                source_program.steps[source_step_index]
                if source_program is not None
                and 0 <= source_step_index < len(source_program.steps)
                else None
            )
            target_step = (
                target_program.steps[target_step_index]
                if target_program is not None
                and 0 <= target_step_index < len(target_program.steps)
                else None
            )
            after_source = self._step_signature(source_step)
            after_target = self._step_signature(target_step)
            record = {
                "consult_no": before["number"],
                "source": [before["source_index"], source_index],
                "target": [before["target_index"], target_index],
                "source_preserved": after_source == before["source_signature"],
                "target_preserved": after_target == before["target_signature"]
            }
            remap_audit.append(record)
            if before["source_signature"] is None:
                errors.append(
                    f"CONSULT_SOURCE_INVALID_BEFORE: C{before['number']} "
                    f"M{source_mid} INDEX {before['source_index']}"
                )
            elif after_source != before["source_signature"]:
                errors.append(
                    f"CONSULT_SOURCE_REMAP_MISMATCH: C{before['number']} "
                    f"M{source_mid} {before['source_index']}->{source_index}"
                )
            if before["target_signature"] is None:
                errors.append(
                    f"CONSULT_TARGET_INVALID_BEFORE: C{before['number']} "
                    f"M{target_mid} INDEX {before['target_index']}"
                )
            elif after_target != before["target_signature"]:
                errors.append(
                    f"CONSULT_TARGET_REMAP_MISMATCH: C{before['number']} "
                    f"M{target_mid} {before['target_index']}->{target_index}"
                )
        return errors, remap_audit

    def transform(self, programs, consults, candidate,
                  approach_positions_by_source=None):
        consults = list(consults or [])
        binding_snapshots = self._consult_binding_snapshot(programs, consults)
        transformed_programs = deepcopy(programs)
        transformed_consults = deepcopy(consults)
        outcome = ProgramTransformationResult(
            programs=transformed_programs,
            consults=transformed_consults
        )
        outcome.errors.extend(self._validate_candidate(candidate))
        outcome.errors.extend(self._validate_parking_bath(candidate))
        if outcome.errors:
            return outcome

        insertion_points = self._insertion_points(transformed_consults)
        approach_positions_by_source = approach_positions_by_source or {}
        actual_insertions = {mid: [] for mid in transformed_programs}

        for manipulator_id, program in transformed_programs.items():
            manipulator_id = int(manipulator_id)
            start_position = int(candidate.start_positions[manipulator_id - 1])
            parking_position = int(candidate.parking_positions[manipulator_id - 1])

            start_hold = next(
                (step for step in program.steps if self._is_start_hold(step)),
                None
            )
            if start_hold is None:
                start_hold = self._parking_step(
                    program, start_position,
                    "CYCLE_START_HOLD", "POSTOJ_START"
                )
                program.steps.insert(0, start_hold)
                outcome.inserted_steps += 1
                outcome.notes.append(
                    f"M{manipulator_id}: inserted CYCLE_START_HOLD at ST{start_position}."
                )
                # Existing consult indexes refer to the old program.
                actual_insertions[manipulator_id].append(0)
            else:
                self._set_step_station(program, start_hold, start_position)

            # Redirect existing parking commands, excluding technical transfer
            # and the explicit cycle start hold.
            for step in program.steps:
                if self._is_start_hold(step):
                    continue
                if not self._is_empty_parking(step):
                    continue
                if str(getattr(step, "status", "")).startswith("TRANSFER_"):
                    continue
                self._set_step_station(program, step, parking_position)
                step.status = "OPTIMIZER_PARKING"

            # Insert preposition before original consult-protected steps. Work in
            # descending order so original step indexes remain stable.
            points = sorted(insertion_points.get(manipulator_id, set()), reverse=True)
            start_offset = 1 if actual_insertions[manipulator_id] else 0
            for original_point in points:
                insertion_index = original_point + start_offset
                if insertion_index < 0 or insertion_index >= len(program.steps):
                    outcome.errors.append(
                        f"CONSULT_SOURCE_OUT_OF_RANGE: M{manipulator_id} "
                        f"step={original_point + 1}"
                    )
                    continue
                previous_station = (
                    int(program.steps[insertion_index - 1].station_id)
                    if insertion_index > 0
                    else start_position
                )
                approach = approach_positions_by_source.get(
                    (manipulator_id, self._step_index_to_plc_index(original_point))
                )
                approach_position = int(getattr(
                    approach, "approach_position", approach
                )) if approach is not None else parking_position
                if previous_station == approach_position:
                    continue
                if not self.path_validator(
                    manipulator_id, previous_station, approach_position
                ):
                    outcome.notes.append(
                        f"M{manipulator_id}: preposition to ST{approach_position} "
                        "skipped by path validator."
                    )
                    continue
                protected = program.steps[insertion_index]
                preposition = self._parking_step(
                    program,
                    approach_position,
                    "OPTIMIZER_CONSULT_PREPOSITION",
                    "CONSULT_PREPOSITION",
                    getattr(protected, "cycle_time_start", 0.0)
                )
                program.steps.insert(insertion_index, preposition)
                actual_insertions[manipulator_id].append(original_point)
                outcome.inserted_steps += 1
                outcome.notes.append(
                    f"M{manipulator_id}: preposition ST{previous_station}->"
                    f"ST{approach_position} before PLC step {original_point + 1}."
                )

            # Explicitly close the position cycle. This movement is measured as
            # part of the PLC cycle, never appended after KPI calculation.
            if program.steps:
                last_step = program.steps[-1]
                last_position = int(last_step.station_id)
                if (
                    last_position != start_position
                    and int(getattr(last_step, "action", self.ACTION_DROP))
                    == self.ACTION_PICKUP
                    and not self._is_empty_parking(last_step)
                ):
                    outcome.errors.append(
                        f"CYCLE_RETURN_AFTER_PICKUP_UNSAFE: M{manipulator_id} "
                        f"last=ST{last_position}"
                    )
                elif last_position != start_position:
                    if self.path_validator(
                        manipulator_id, last_position, start_position
                    ):
                        program.steps.append(self._parking_step(
                            program,
                            start_position,
                            "OPTIMIZER_CYCLE_RETURN",
                            "POWROT_CYKL"
                        ))
                        outcome.inserted_steps += 1
                        outcome.notes.append(
                            f"M{manipulator_id}: cycle return ST{last_position}->"
                            f"ST{start_position}."
                        )
                    else:
                        outcome.errors.append(
                            f"CYCLE_RETURN_PATH_BLOCKED: M{manipulator_id} "
                            f"ST{last_position}->ST{start_position}"
                        )
            self._renumber(program)
            raw_word_count = len(program.steps) * self.WORDS_PER_STEP
            if raw_word_count > program.max_program_words:
                outcome.errors.append(
                    f"PROGRAM_WORD_LIMIT: M{manipulator_id} uses "
                    f"{raw_word_count}/{program.max_program_words} WORD."
                )

        # Remap both sides of every consult using insertions in the referenced
        # manipulator program. The protected source operation moves after the
        # newly inserted preposition, so the consult never blocks preposition.
        for consult in transformed_consults:
            source_mid = int(getattr(consult, "source_manipulator_id"))
            target_mid = int(getattr(consult, "target_manipulator_id"))
            source_index = int(getattr(consult, "source_plc_index"))
            target_index = int(getattr(consult, "target_plc_index"))
            new_source = self._remap_plc_index(
                source_index, actual_insertions.get(source_mid, [])
            )
            new_target = self._remap_plc_index(
                target_index, actual_insertions.get(target_mid, [])
            )
            self._set_consult_value(consult, "source_plc_index", new_source)
            self._set_consult_value(consult, "target_plc_index", new_target)
            source_program = transformed_programs.get(source_mid)
            target_program = transformed_programs.get(target_mid)
            if source_program is not None:
                self._set_consult_value(
                    consult, "source_logical_step_no",
                    self._plc_index_to_step_index(new_source) + 1
                )
                self._set_consult_value(
                    consult, "source_word_address",
                    int(source_program.index_address) + new_source
                )
            if target_program is not None:
                self._set_consult_value(
                    consult, "target_logical_step_no",
                    self._plc_index_to_step_index(new_target) + 1
                )
                self._set_consult_value(
                    consult, "target_word_address",
                    int(target_program.index_address) + new_target
                )

        audit_errors, remap_audit = self._audit_consult_bindings(
            transformed_programs,
            transformed_consults,
            binding_snapshots
        )
        outcome.errors.extend(audit_errors)
        outcome.notes.append(
            f"CONSULT_REMAP_AUDIT: {len(remap_audit)} consults, "
            f"errors={len(audit_errors)}"
        )
        outcome.consult_remap_audit = remap_audit
        return outcome
