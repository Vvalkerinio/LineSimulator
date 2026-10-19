import argparse
import contextlib
import json
from pathlib import Path

from src.analysis.kpi_engine import KPIEngine
from src.analysis.manipulator_separation_report import ManipulatorSeparationReport
from src.core.event_driven_simulator import EventDrivenSimulator
from src.core.simulation_debug import debug_mode
from src.io.configuration_serializer import load_configuration


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', default='configs/default.json')
    parser.add_argument('--log', default='headless_event.log')
    parser.add_argument('--shared-group', default='ODT')
    parser.add_argument('--shared-mode', default='percent')
    parser.add_argument('--shared-value', type=float, default=90.0)
    parser.add_argument('--feed-duration', type=float, default=3600.0)
    args = parser.parse_args()

    config = load_configuration(args.config)
    config.infinite_feed = True
    config.feed_duration = args.feed_duration
    for station in config.stations:
        if getattr(station, 'shared_bath_group', None) == args.shared_group:
            station.shared_bath_stagger_mode = args.shared_mode
            station.shared_bath_stagger_value = args.shared_value

    with open(args.log, 'w', encoding='utf-8') as output:
        with contextlib.redirect_stdout(output):
            with debug_mode(True):
                result = EventDrivenSimulator(config).run()
            KPIEngine().calculate(result, config.pieces_per_transport)

    separation = ManipulatorSeparationReport().analyze(result, config)
    summary = {
        'events': result.processed_events,
        'tasks': len(result.manipulator_tasks),
        'deadlocks': len(result.deadlocks),
        'completed_hangers': len(getattr(result, 'hanger_exit_times', {})),
        'minimum_distance': separation.minimum_distance,
        'required_distance': separation.required_spacing,
        'separation_status': separation.status,
        'track_safety_violation': bool(
            separation.status == 'COLLISION'
            or separation.minimum_distance + 1e-6 < separation.required_spacing
        ),
        'precise_transports_per_hour': float(
            (getattr(result, 'steady_state', None) or {}).get(
                'interval_throughput', 0.0
            ) or 0.0
        ),
    }
    print(json.dumps(summary, indent=2))
    raise SystemExit(1 if summary['track_safety_violation'] else 0)


if __name__ == '__main__':
    main()
