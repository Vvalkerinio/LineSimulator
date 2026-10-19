# RELEASE NOTES 1.1.0a8.40

## Parking safety
- Scheduler evaluates all legal non-process return positions instead of only the first preferred position.
- Return endpoint is checked against current manipulator positions and minimum_manipulator_spacing.
- Commit revalidates static occupancy before reserving and executing a transport.
- Shared-zone handoff points are excluded from persistent process-bath parking candidates.

## Theoretical throughput
- Precise EventDriven is sourced from interval_throughput based on physical HANGER_EXIT intervals.
- Rounded steady-state window throughput is not used as achieved throughput.
- All theoretical capacity, resource bounds and gaps are rendered in szt/h.
- Conversion uses pieces_per_transport from Simulation settings.
- Precise transports/h remains printed as a diagnostic line.
