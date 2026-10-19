from src.analysis.text_table_utils import format_text_table
from src.model.station_numbering import display_station_id


class StationResidenceReport:
    STATUSES = (
        "TRADEOFF_MIN", "TRADEOFF_MAX",
        "HARD_MIN_VIOLATION", "HARD_MAX_VIOLATION",
    )

    @staticmethod
    def _status(record):
        return str(getattr(record, "compliance_status",
                           getattr(record, "violation_type", "OK")))

    def print_summary(self, result, config=None):
        records = list(getattr(result, "process_compliance", []))
        if not records:
            return
        names = {int(s.id): s.name for s in getattr(config, "stations", [])} if config else {}
        grouped = {}
        for record in records:
            grouped.setdefault(int(record.station_id), []).append(record)
        totals = {status: 0 for status in self.STATUSES}
        rows = []
        for station_id in sorted(grouped):
            station_records = grouped[station_id]
            actual = [float(r.actual_time) for r in station_records]
            counts = {status: sum(self._status(r) == status for r in station_records)
                      for status in self.STATUSES}
            for status, count in counts.items():
                totals[status] += count
            first = station_records[0]
            hard_total = counts["HARD_MIN_VIOLATION"] + counts["HARD_MAX_VIOLATION"]
            rows.append([
                str(display_station_id(station_id)), names.get(station_id, ""),
                str(len(station_records)), f"{sum(actual)/len(actual):.1f}",
                f"{min(actual):.1f}", f"{max(actual):.1f}",
                f"{float(first.min_time):.1f}", f"{float(first.max_time):.1f}",
                str(counts["TRADEOFF_MIN"]), str(counts["TRADEOFF_MAX"]),
                str(counts["HARD_MIN_VIOLATION"]), str(counts["HARD_MAX_VIOLATION"]),
                str(hard_total),
            ])
        print()
        print("=" * 132)
        print("STATION RESIDENCE TIME REPORT")
        print("=" * 132)
        print(format_text_table(
            ["Station", "Name", "Count", "Avg[s]", "Min[s]", "Max[s]",
             "NomMin", "NomMax", "TrMin", "TrMax", "HardMin", "HardMax", "HardTotal"],
            rows,
            ["right", "left", "right", "right", "right", "right",
             "right", "right", "right", "right", "right", "right", "right"]
        ))
        total_hard = totals["HARD_MIN_VIOLATION"] + totals["HARD_MAX_VIOLATION"]
        print()
        print("COMPLIANCE TOTALS: "
              f"TradeMin={totals['TRADEOFF_MIN']} "
              f"TradeMax={totals['TRADEOFF_MAX']} "
              f"HardMin={totals['HARD_MIN_VIOLATION']} "
              f"HardMax={totals['HARD_MAX_VIOLATION']} "
              f"ProcessViolations={total_hard}")
        print()
        print("TOP 10 PROCESS TRADEOFFS / VIOLATIONS")
        non_ok = [r for r in records if self._status(r) != "OK"]
        non_ok.sort(key=lambda r: float(getattr(r, "nominal_deviation", 0.0)), reverse=True)
        detail_rows = []
        for r in non_ok[:10]:
            possible_min = getattr(r, "possible_min_time", None)
            possible_max = getattr(r, "possible_max_time", None)
            possible = "-" if possible_min is None or possible_max is None else f"{float(possible_min):.1f}..{float(possible_max):.1f}"
            detail_rows.append([
                f"H{r.hanger_id}", str(display_station_id(r.station_id)),
                names.get(int(r.station_id), ""), f"{float(r.actual_time):.1f}",
                possible, f"{float(r.min_time):.1f}..{float(r.max_time):.1f}",
                self._status(r), f"{float(getattr(r, 'nominal_deviation', 0.0)):.1f}"
            ])
        if detail_rows:
            print(format_text_table(
                ["Hanger", "Station", "Name", "Actual[s]", "Possible[s]",
                 "Nominal[s]", "Status", "Deviation[s]"],
                detail_rows,
                ["left", "right", "left", "right", "right", "right", "left", "right"]
            ))
        print("=" * 132)
