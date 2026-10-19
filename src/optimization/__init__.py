"""Optimization foundations for Line Simulator."""

from .optimization_candidate import OptimizationCandidate
from .optimization_constraints import OptimizationConstraints, ConstraintViolation
from .parking_position_selector import ParkingPositionSelector, ParkingDecision
from .consult_safe_approach_planner import ConsultSafeApproachPlanner, ApproachPlan
from .consult_wait_analyzer import ConsultWaitAnalyzer
from .cycle_closure_validator import CycleClosureValidator
from .candidate_generator import CandidateGenerator
from .optimization_runner import OptimizationRunner, CandidateResult
from .program_candidate_evaluator import ProgramCandidateEvaluator
from .program_candidate_transformer import (
    ProgramCandidateTransformer,
    ProgramTransformationResult
)
from .trajectory_aware_preposition_planner import (
    TrajectoryAwarePrepositionPlanner,
    ConsultApproachDecision
)
from .trajectory_aware_optimization_pipeline import (
    TrajectoryAwareOptimizationPipeline
)
from .optimization_cache import OptimizationCache
from .optimization_result_codec import OptimizationResultCodec
from .optimization_study import (
    OptimizationStudy,
    OptimizationStudySettings,
    OptimizationStudyResult
)
from .optimization_report import OptimizationReport
from .optimization_study_factory import OptimizationStudyFactory
from .event_driven_candidate import (
    EventDrivenCandidate,
    SharedBathCandidateParameter
)
from .shared_bath_parameter_generator import SharedBathParameterGenerator
from .event_driven_candidate_generator import EventDrivenCandidateGenerator
from .event_driven_candidate_applier import EventDrivenCandidateApplier
from .event_driven_candidate_evaluator import EventDrivenCandidateEvaluator
from .event_driven_program_candidate_builder import (
    EventDrivenProgramCandidateBuilder,
    EventDrivenProgramBuildResult
)
from .generated_program_candidate_evaluator import (
    GeneratedProgramCandidateEvaluator
)
from .event_driven_optimization_study import (
    EventDrivenOptimizationStudy,
    EventDrivenStudySettings,
    EventDrivenStudyResult
)
from .event_driven_optimization_factory import EventDrivenOptimizationFactory
from .reference_program_evaluator import ReferenceProgramEvaluator
from .reference_event_driven_evaluator import ReferenceEventDrivenEvaluator

from .theoretical_candidate_evaluator import TheoreticalCandidateEvaluator
from .theoretical_screening_study import (
    TheoreticalScreeningStudy,
    TheoreticalScreeningSettings,
    TheoreticalScreeningStudyResult
)
