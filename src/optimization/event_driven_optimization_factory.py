import hashlib
import json

from src.optimization.event_driven_candidate_evaluator import EventDrivenCandidateEvaluator
from src.optimization.event_driven_candidate_generator import EventDrivenCandidateGenerator
from src.optimization.event_driven_optimization_study import (
    EventDrivenOptimizationStudy, EventDrivenStudySettings
)
from src.optimization.optimization_constraints import OptimizationConstraints
from src.optimization.shared_bath_parameter_generator import SharedBathParameterGenerator
from src.optimization.theoretical_candidate_evaluator import (
    TheoreticalCandidateEvaluator
)
from src.optimization.theoretical_screening_study import (
    TheoreticalScreeningStudy,
    TheoreticalScreeningSettings
)
from src.optimization.reference_event_driven_evaluator import (
    ReferenceEventDrivenEvaluator
)


class EventDrivenOptimizationFactory:
    SCHEMA = "event-driven-new-plc-v1"

    def __init__(self, configuration, programs_provider=None, consults_provider=None):
        self.configuration = configuration
        self.programs_provider = programs_provider or (lambda: {})
        self.consults_provider = consults_provider or (lambda: [])

    def fingerprint(self):
        payload = {
            "schema": self.SCHEMA,
            "stations": [[int(s.id), bool(s.enabled), float(s.min_process_time),
                          float(s.max_process_time), float(getattr(s, "drip_time", 0)),
                          str(getattr(s, "shared_bath_group", "") or "")]
                         for s in self.configuration.stations],
            "manipulators": [[int(m.id), int(m.position), int(m.work_zone_start),
                              int(m.work_zone_end), float(m.lift_time),
                              float(m.drop_time), float(m.travel_time_per_position)]
                             for m in self.configuration.manipulators],
            "spacing": float(self.configuration.minimum_manipulator_spacing)
        }
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def candidate_factory(self):
        from itertools import islice
        shared = SharedBathParameterGenerator()
        generated = EventDrivenCandidateGenerator(
            OptimizationConstraints(self.configuration.minimum_manipulator_spacing),
            shared
        ).generate(self.configuration)
        # The first generated item is the exact, unmodified EventDriven state.
        # Optimization now ranks modified EventDriven configurations only.
        return islice(generated, 1, None)

    def build(self, ui_settings, progress_callback, cancel_requested):
        event = EventDrivenCandidateEvaluator(self.configuration)
        mode = str(ui_settings.get("optimization_mode", "event")).lower()
        if mode == "theoretical":
            return TheoreticalScreeningStudy(
                TheoreticalCandidateEvaluator(self.configuration),
                event,
                TheoreticalScreeningSettings(
                    screening_limit=int(ui_settings.get("screening_limit", 5000)),
                    finalist_count=int(ui_settings.get("finalist_count", 20))
                ),
                progress_callback=progress_callback,
                cancel_requested=cancel_requested
            )
        return EventDrivenOptimizationStudy(
            event, None,
            EventDrivenStudySettings(
                screening_limit=int(ui_settings.get("screening_limit", 500)),
                finalist_count=0
            ),
            progress_callback=progress_callback,
            cancel_requested=cancel_requested,
            reference_evaluator=ReferenceEventDrivenEvaluator(
                self.configuration
            ),
            reference_candidate=next(
                EventDrivenCandidateGenerator(
                    OptimizationConstraints(
                        self.configuration.minimum_manipulator_spacing
                    ),
                    SharedBathParameterGenerator()
                ).generate(self.configuration)
            )
        )

    def evaluate_candidate(self, candidate, cycles=8):
        return EventDrivenCandidateEvaluator(self.configuration)(candidate)
