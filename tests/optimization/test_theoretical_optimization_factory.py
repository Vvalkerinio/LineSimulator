from src.io.configuration_serializer import create_default_configuration
from src.optimization.event_driven_optimization_factory import (
    EventDrivenOptimizationFactory,
)
from src.optimization.event_driven_optimization_study import (
    EventDrivenOptimizationStudy,
)
from src.optimization.theoretical_screening_study import (
    TheoreticalScreeningStudy,
)


def factory():
    return EventDrivenOptimizationFactory(create_default_configuration())


def test_factory_builds_full_event_mode_by_default():
    study = factory().build({}, None, lambda: False)
    assert isinstance(study, EventDrivenOptimizationStudy)


def test_factory_builds_theoretical_screening_mode():
    study = factory().build({
        "optimization_mode": "theoretical",
        "screening_limit": 1234,
        "finalist_count": 17,
    }, None, lambda: False)
    assert isinstance(study, TheoreticalScreeningStudy)
    assert study.settings.screening_limit == 1234
    assert study.settings.finalist_count == 17
