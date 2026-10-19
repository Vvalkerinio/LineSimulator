from src.model.station_numbering import display_station_id
from math import isclose, isfinite

from src.core.process_limit_classifier import assess_process_time

from src.model.event_type import EventType


class ProgramResidenceAuditError(RuntimeError):
    """Raised when ProgramDriven residence data is inconsistent."""


class ProgramResidenceAuditor:
    """Fail-fast validation of ProgramDriven bath residence records.

    Residence is DROP_FINISH to PICKUP_FINISH. Drip starts afterwards and is
    excluded. Virtual transfer stations 23/24 are never process baths.
    """

    EPSILON = 1e-6
    EXCLUDED_STATIONS = {23, 24}

    def audit(self, result, configuration, strict=True):
        records = list(getattr(result, "process_compliance", []))
        entry_times = dict(getattr(result, "station_entry_times", {}))
        transport_entries = {
            (
                int(event.hanger_id),
                int(event.target_station),
                float(event.time)
            )
            for event in getattr(result, "events", [])
            if event.event_type == EventType.TRANSPORT_END
            and event.hanger_id is not None
            and event.target_station is not None
        }
        station_map = {
            int(station.id): station
            for station in getattr(configuration, "stations", [])
        }
        errors = []
        seen = set()

        for index, record in enumerate(records):
            station_id = int(record.station_id)
            prefix = f"record[{index}] H={record.hanger_id} S={display_station_id(station_id)}"
            identity = (
                int(record.hanger_id), station_id,
                float(record.entry_time), float(record.exit_time)
            )
            if identity in seen:
                errors.append(f"{prefix}: duplicate residence record")
            seen.add(identity)

            values = [record.entry_time, record.exit_time, record.actual_time,
                      record.min_time, record.max_time]
            if not all(isfinite(float(value)) for value in values):
                errors.append(f"{prefix}: non-finite numeric value")
                continue
            if station_id in self.EXCLUDED_STATIONS:
                errors.append(f"{prefix}: virtual transfer station in bath report")

            station = station_map.get(station_id)
            if station is None:
                errors.append(f"{prefix}: station missing from configuration")
                continue

            actual = float(record.exit_time) - float(record.entry_time)
            if actual < -self.EPSILON:
                errors.append(f"{prefix}: exit earlier than entry")
            if not isclose(float(record.actual_time), actual,
                           rel_tol=0.0, abs_tol=self.EPSILON):
                errors.append(
                    f"{prefix}: actual={record.actual_time} but exit-entry={actual}"
                )

            # Normal residence entries must have independent evidence in the
            # transport event stream. Negative entries are intentional prefill
            # timestamps created before t=0 and cannot have a transport event.
            if float(record.entry_time) >= 0.0:
                has_event_evidence = any(
                    hanger_id == int(record.hanger_id)
                    and target_station == station_id
                    and isclose(
                        event_time,
                        float(record.entry_time),
                        rel_tol=0.0,
                        abs_tol=self.EPSILON
                    )
                    for hanger_id, target_station, event_time
                    in transport_entries
                )
                if not has_event_evidence:
                    errors.append(
                        f"{prefix}: missing TRANSPORT_END entry evidence"
                    )
            else:
                source = entry_times.get((record.hanger_id, station_id))
                if source is None or not isclose(
                    float(record.entry_time), float(source),
                    rel_tol=0.0, abs_tol=self.EPSILON
                ):
                    errors.append(
                        f"{prefix}: missing synthetic prefill entry evidence"
                    )

            expected_min = float(getattr(station, "min_process_time", 0.0))
            expected_max = float(getattr(station, "max_process_time", 999999.0))
            if not isclose(float(record.min_time), expected_min,
                           rel_tol=0.0, abs_tol=self.EPSILON):
                errors.append(f"{prefix}: min specification mismatch")
            if not isclose(float(record.max_time), expected_max,
                           rel_tol=0.0, abs_tol=self.EPSILON):
                errors.append(f"{prefix}: max specification mismatch")

            assessment = assess_process_time(station, actual)
            min_ok = assessment.nominal_min_ok
            max_ok = assessment.nominal_max_ok
            if bool(record.min_ok) != min_ok:
                errors.append(f"{prefix}: min_ok mismatch")
            if bool(record.max_ok) != max_ok:
                errors.append(f"{prefix}: max_ok mismatch")
            if str(record.violation_type) != assessment.status:
                errors.append(f"{prefix}: violation_type mismatch")
            if bool(getattr(record, "possible_min_ok", True)) != assessment.possible_min_ok:
                errors.append(f"{prefix}: possible_min_ok mismatch")
            if bool(getattr(record, "possible_max_ok", True)) != assessment.possible_max_ok:
                errors.append(f"{prefix}: possible_max_ok mismatch")

        audit = {
            "valid": not errors,
            "record_count": len(records),
            "definition": "DROP_FINISH_TO_PICKUP_FINISH",
            "drip_excluded": True,
            "excluded_stations": sorted(self.EXCLUDED_STATIONS),
            "errors": errors
        }
        result.program_residence_audit = audit
        if strict and errors:
            raise ProgramResidenceAuditError(
                "ProgramDriven residence audit failed:\n- "
                + "\n- ".join(errors)
            )
        return audit
