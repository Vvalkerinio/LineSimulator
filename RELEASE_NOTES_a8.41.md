# RELEASE NOTES 1.1.0a8.41

## Transport-aware ideal process ceiling
- Corrected the definition of Ideal Process / Perfect Manipulators.
- Each ideal route stage now uses: residence + outbound lift + source drip + loaded travel + drop.
- A suitable manipulator is assumed immediately available at every pickup.
- Empty approach, collisions, passing, spacing, queues, parking and reservations remain ignored.
- The ideal ceiling is now sensitive to lift_time, drop_time and travel_time_per_position.
- Parallel shared-bath members add their ideal stage capacities.
- The report identifies the nominal and possible ideal bottleneck resources.
