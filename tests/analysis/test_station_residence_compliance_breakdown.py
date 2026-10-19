from types import SimpleNamespace

from src.analysis.station_residence_report import StationResidenceReport


def record(status, actual, deviation=0.0):
    return SimpleNamespace(
        hanger_id=1, station_id=3, actual_time=actual,
        min_time=50.0, max_time=90.0,
        possible_min_time=40.0, possible_max_time=100.0,
        compliance_status=status, violation_type=status,
        nominal_deviation=deviation,
    )


def test_residence_report_reconciles_all_compliance_statuses(capsys):
    records = [
        record("OK", 60.0),
        record("TRADEOFF_MIN", 45.0, 5.0),
        record("TRADEOFF_MAX", 95.0, 5.0),
        record("HARD_MIN_VIOLATION", 20.0, 30.0),
        record("HARD_MAX_VIOLATION", 120.0, 30.0),
    ]
    config = SimpleNamespace(stations=[SimpleNamespace(id=3, name="Bath")])
    StationResidenceReport().print_summary(
        SimpleNamespace(process_compliance=records), config
    )
    output = capsys.readouterr().out
    assert all(label in output for label in ("TrMin", "TrMax", "HardMin", "HardMax", "HardTotal"))
    assert "TradeMin=1 TradeMax=1 HardMin=1 HardMax=1 ProcessViolations=2" in output
    assert "TOP 10 PROCESS TRADEOFFS / VIOLATIONS" in output
    assert "Bath" in output and "H1" in output
    assert "40.0..100.0" in output
