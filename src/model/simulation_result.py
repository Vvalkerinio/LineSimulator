from dataclasses import (
    dataclass,
    field
)

from src.model.event import (
    Event
)

from src.model.manipulator_task import (
    ManipulatorTask
)

from src.model.manipulator_position_sample import (
    ManipulatorPositionSample
)


@dataclass
class SimulationResult:

    events: list[Event] = field(
        default_factory=list
    )

    manipulator_tasks: list[
        ManipulatorTask
    ] = field(
        default_factory=list
    )

    manipulator_samples: list[
        ManipulatorPositionSample
    ] = field(
        default_factory=list
    )

    timeline_segments: list = field(
        default_factory=list
    )

    throughput_windows: list = field(
        default_factory=list
    )

    steady_state: dict | None = None

    final_time: float = 0.0

    processed_events: int = 0

    scheduled_transports: int = 0

    completed_transports: int = 0

    total_process_time: float = 0.0

    process_violations: list = field(
        default_factory=list
    )

    generated_hangers: int = 0

    deadlocks: list = field(
        default_factory=list
    )
    
    process_compliance: list = field(
        default_factory=list
    )