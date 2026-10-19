import hashlib
import json
from itertools import product
from pathlib import Path

from src.optimization.candidate_generator import CandidateGenerator
from src.optimization.optimization_candidate import OptimizationCandidate
from src.optimization.optimization_cache import OptimizationCache
from src.optimization.optimization_constraints import OptimizationConstraints
from src.optimization.optimization_study import (
    OptimizationStudy,
    OptimizationStudySettings
)
from src.optimization.program_candidate_evaluator import ProgramCandidateEvaluator
from src.optimization.program_candidate_transformer import ProgramCandidateTransformer
from src.optimization.trajectory_aware_optimization_pipeline import (
    TrajectoryAwareOptimizationPipeline
)
from src.optimization.trajectory_aware_preposition_planner import (
    TrajectoryAwarePrepositionPlanner
)


class OptimizationStudyFactory:
    """Build all optimizer services from the current GUI project state."""

    CACHE_SCHEMA_VERSION = "optimizer-a7.3-consult-binding-audit-phase-diagnostics"

    def __init__(self, configuration, programs_provider, consults_provider,
                 cache_root="optimization_runs"):
        self.configuration = configuration
        self.programs_provider = programs_provider
        self.consults_provider = consults_provider
        self.cache_root = Path(cache_root)

    @staticmethod
    def _program_payload(programs):
        return {
            str(mid): {
                "index_address": int(program.index_address),
                "station_offset": int(program.station_offset),
                "station_id_shift": int(program.station_id_shift),
                "steps": [
                    [int(step.station_id), int(step.action),
                     int(step.wait_time_01s), str(step.status)]
                    for step in program.steps
                ]
            }
            for mid, program in sorted(programs.items())
        }

    @staticmethod
    def _consult_payload(consults):
        return [
            [
                int(item.source_manipulator_id),
                int(item.source_plc_index),
                int(item.target_manipulator_id),
                int(item.target_plc_index),
                str(getattr(item, "reason", "IMPORTED_TXT"))
            ]
            for item in consults
        ]

    def fingerprint(self, programs, consults):
        payload = {
            "optimizer_schema": self.CACHE_SCHEMA_VERSION,
            "stations": [
                [int(item.id), bool(item.enabled),
                 float(item.min_process_time), float(item.max_process_time),
                 float(getattr(item, "drip_time", 0.0)),
                 bool(getattr(item, "is_process_bath", True))]
                for item in self.configuration.stations
            ],
            "manipulators": [
                [int(item.id), int(item.work_zone_start),
                 int(item.work_zone_end), float(item.lift_time),
                 float(item.drop_time),
                 float(item.travel_time_per_position)]
                for item in self.configuration.manipulators
            ],
            "minimum_spacing": float(
                self.configuration.minimum_manipulator_spacing
            ),
            "programs": self._program_payload(programs),
            "consults": self._consult_payload(consults)
        }
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def candidate_factory(self):
        constraints = OptimizationConstraints(
            self.configuration.minimum_manipulator_spacing
        )
        generator = CandidateGenerator(constraints)
        parking = {}
        for manipulator in self.configuration.manipulators:
            legal = [
                int(station.id)
                for station in self.configuration.stations
                if manipulator.work_zone_start <= station.id <= manipulator.work_zone_end
                and not bool(getattr(station, "is_process_bath", True))
            ]
            if not legal:
                legal = list(range(
                    int(manipulator.work_zone_start),
                    int(manipulator.work_zone_end) + 1
                ))
            parking[int(manipulator.id)] = legal
        manipulators = sorted(
            self.configuration.manipulators,
            key=lambda item: int(item.id)
        )
        current_start = tuple(int(item.position) for item in manipulators)

        def ordered_candidates():
            seen = set()
            # The current, already proven ProgramDriven start state is always
            # evaluated first. With a screening limit this prevents the search
            # from spending all slots on one lexicographic corner of the grid.
            if not constraints.validate_positions(current_start, manipulators):
                for parking_positions in product(*[
                    parking[int(item.id)] for item in manipulators
                ]):
                    if constraints.validate_positions(
                        parking_positions, manipulators
                    ):
                        continue
                    candidate = OptimizationCandidate(
                        current_start,
                        tuple(int(value) for value in parking_positions)
                    )
                    key = (
                        candidate.start_positions,
                        candidate.parking_positions
                    )
                    seen.add(key)
                    yield candidate
            for candidate in generator.generate(
                manipulators,
                parking_positions_by_manipulator=parking
            ):
                key = (
                    candidate.start_positions,
                    candidate.parking_positions
                )
                if key in seen:
                    continue
                seen.add(key)
                yield candidate

        return ordered_candidates()

    def build(self, ui_settings, progress_callback, cancel_requested):
        programs = self.programs_provider()
        consults = self.consults_provider()
        if not programs:
            raise ValueError("Najpierw wygeneruj lub zaimportuj program PLC.")
        settings = OptimizationStudySettings(
            screening_limit=int(ui_settings["screening_limit"]),
            finalist_count=int(ui_settings["finalist_count"]),
            screening_cycles=int(ui_settings["screening_cycles"]),
            final_cycles=int(ui_settings["final_cycles"])
        )
        transformer = ProgramCandidateTransformer(self.configuration)
        planner = TrajectoryAwarePrepositionPlanner(self.configuration)

        def pipeline(cycles):
            baseline = ProgramCandidateEvaluator(
                self.configuration, programs, consults,
                cycles=cycles, initial_state_mode="cycle"
            )
            transformed = ProgramCandidateEvaluator(
                self.configuration, programs, consults,
                cycles=cycles, initial_state_mode="cycle"
            )
            return TrajectoryAwareOptimizationPipeline(
                baseline, transformed, planner, transformer
            ).evaluate

        cache = None
        if bool(ui_settings.get("use_cache", True)):
            fingerprint = self.fingerprint(programs, consults)
            cache = OptimizationCache(
                self.cache_root / fingerprint[:16], fingerprint
            )
        return OptimizationStudy(
            screening_evaluator=pipeline(settings.screening_cycles),
            final_evaluator=pipeline(settings.final_cycles),
            settings=settings,
            cache=cache,
            progress_callback=progress_callback,
            cancel_requested=cancel_requested
        )

    def evaluate_candidate(self, candidate, cycles=8):
        """Recalculate one candidate with full objects for preview/application."""
        programs = self.programs_provider()
        consults = self.consults_provider()
        if not programs:
            raise ValueError("Brak programu PLC do zastosowania wariantu.")
        transformer = ProgramCandidateTransformer(self.configuration)
        planner = TrajectoryAwarePrepositionPlanner(self.configuration)
        baseline = ProgramCandidateEvaluator(
            self.configuration, programs, consults,
            cycles=cycles, initial_state_mode="cycle"
        )
        transformed = ProgramCandidateEvaluator(
            self.configuration, programs, consults,
            cycles=cycles, initial_state_mode="cycle"
        )
        return TrajectoryAwareOptimizationPipeline(
            baseline, transformed, planner, transformer
        ).evaluate(candidate)
