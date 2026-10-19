# Line Simulator v1.1.0a8.20

## Performance and Shared Bath retry release

### Debug logging
- Added a `Debug log` checkbox to the Simulation tab.
- Debug logging is disabled by default.
- Added context-local logging state based on `ContextVar`.
- Hot-path messages use lazy `debug_print(lambda: ...)` factories.
- Scheduler, assignment, Shared Bath, retry, predictive pickup, YIELD and Track Guard diagnostics no longer format or print messages with Debug disabled.
- Final simulation reports remain enabled.

### Shared Bath retry scheduling
- Added `SharedBathSelector.earliest_group_availability()`.
- A blocked group retries at the earliest known release of any parallel bath.
- The 30-second retry interval remains a fallback when no finite release is known.
- Retry scheduling guarantees at least one second of simulated-time progress.
- Added retry diagnostics: executed retries, avoided fixed intervals and average retry delay.

### Trajectory performance
- Added per-manipulator segment indexes and start-time indexes.
- `TrajectoryManager.position_at()` now uses binary search.
- Added `segments_overlapping()` for local interval queries.
- Added trajectory revision counter.

### Event-track safety performance
- Cached ordered manipulators and M1-M4 neighbor relationships.
- Safety breakpoint checks now use only time-overlapping trajectory segments.

### Validation
- Python source and tests compile successfully.
- 265 regression tests passed, 0 failed.
- The 265-test regression includes the new Debug, Shared Bath retry and trajectory-index tests.
- GUI-heavy tests excluded by the established backend regression profile remain unchanged.
