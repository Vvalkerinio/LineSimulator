from types import SimpleNamespace
import pytest
from src.analysis.program_residence_auditor import ProgramResidenceAuditor, ProgramResidenceAuditError
from src.model.process_compliance_record import ProcessComplianceRecord
from src.model.simulation_result import SimulationResult
from src.model.event import Event
from src.model.event_type import EventType


def configuration():
    return SimpleNamespace(stations=[SimpleNamespace(id=5, min_process_time=10.0, max_process_time=20.0)])


def valid_result():
    result = SimulationResult()
    result.station_entry_times = {(1, 5): 100.0}
    result.events = [Event(
        time=100.0,
        event_type=EventType.TRANSPORT_END,
        manipulator_id=1,
        hanger_id=1,
        source_station=4,
        target_station=5
    )]
    result.process_compliance = [ProcessComplianceRecord(
        hanger_id=1, station_id=5, entry_time=100.0, exit_time=115.0,
        actual_time=15.0, min_time=10.0, max_time=20.0,
        min_ok=True, max_ok=True, violation_type="OK")]
    return result


def test_valid_residence_is_independently_audited():
    audit = ProgramResidenceAuditor().audit(valid_result(), configuration())
    assert audit["valid"] is True
    assert audit["definition"] == "DROP_FINISH_TO_PICKUP_FINISH"
    assert audit["drip_excluded"] is True


def test_actual_must_equal_exit_minus_entry():
    result = valid_result(); result.process_compliance[0].actual_time = 17.0
    with pytest.raises(ProgramResidenceAuditError, match="exit-entry"):
        ProgramResidenceAuditor().audit(result, configuration())


def test_normal_entry_requires_transport_event_evidence():
    result = valid_result(); result.events = []
    with pytest.raises(ProgramResidenceAuditError, match="TRANSPORT_END"):
        ProgramResidenceAuditor().audit(result, configuration())


def test_virtual_transfer_station_is_rejected():
    result = valid_result(); result.process_compliance[0].station_id = 23
    result.station_entry_times = {(1, 23): 100.0}
    with pytest.raises(ProgramResidenceAuditError, match="virtual transfer"):
        ProgramResidenceAuditor().audit(result, configuration())


def test_flags_are_recomputed_from_configuration():
    result = valid_result(); record = result.process_compliance[0]
    record.exit_time = 125.0; record.actual_time = 25.0
    with pytest.raises(ProgramResidenceAuditError, match="max_ok mismatch"):
        ProgramResidenceAuditor().audit(result, configuration())
