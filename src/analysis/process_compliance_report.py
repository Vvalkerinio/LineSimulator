from src.model.station_numbering import display_station_id
class ProcessComplianceReport:

    def print_summary(self, result):
        records = list(getattr(result, "process_compliance", []))
        if not records:
            return
        total = len(records)
        status = lambda r: getattr(r, "compliance_status", getattr(r, "violation_type", "OK"))
        nominal_ok = sum(1 for r in records if status(r) == "OK")
        tradeoff_min = sum(1 for r in records if status(r) == "TRADEOFF_MIN")
        tradeoff_max = sum(1 for r in records if status(r) == "TRADEOFF_MAX")
        hard_min = sum(1 for r in records if status(r) == "HARD_MIN_VIOLATION")
        hard_max = sum(1 for r in records if status(r) == "HARD_MAX_VIOLATION")
        print()
        print("=" * 60)
        print("PROCESS COMPLIANCE REPORT")
        print("=" * 60)
        print(f"Operations                  : {total}")
        print(f"Nominal OK                  : {nominal_ok}")
        print(f"Tradeoff below nominal min  : {tradeoff_min}")
        print(f"Tradeoff above nominal max  : {tradeoff_max}")
        print(f"Hard min violations         : {hard_min}")
        print(f"Hard max violations         : {hard_max}")
        print(f"Nominal compliance          : {nominal_ok / total * 100.0:.2f}%")
        print(f"Possible compliance         : {(total-hard_min-hard_max) / total * 100.0:.2f}%")
        exceptional = [r for r in records if status(r) != "OK"]
        exceptional.sort(key=lambda r: float(getattr(r, "nominal_deviation", 0.0)), reverse=True)
        print()
        print("TOP 10 PROCESS TRADEOFFS / VIOLATIONS")
        for r in exceptional[:10]:
            print(
                f"H={r.hanger_id} S={display_station_id(r.station_id)} actual={r.actual_time:.1f} "
                f"possible=[{r.possible_min_time:.1f}, {r.possible_max_time:.1f}] "
                f"nominal=[{r.min_time:.1f}, {r.max_time:.1f}] "
                f"status={r.compliance_status} deviation={r.nominal_deviation:.1f}"
            )
        print("=" * 60)
