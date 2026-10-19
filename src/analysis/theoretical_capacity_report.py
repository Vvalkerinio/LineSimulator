from math import inf


class TheoreticalCapacityTextReport:
    @staticmethod
    def _number(value):
        return "unbounded" if value == inf else f"{value:.2f} szt/h"

    def render(self, report):
        pieces = max(1, int(getattr(report, "pieces_per_transport", 1)))

        def scale(value):
            return value if value == inf else float(value) * pieces

        lines = [
            "=" * 72,
            "THEORETICAL CAPACITY REPORT",
            "=" * 72,
            f"Pieces per transport          : {pieces}",
            f"Nominal certified upper bound : {self._number(scale(report.nominal_upper_bound))}",
            f"Nominal limiting resource     : {report.nominal_limiting_resource or '-'}",
            f"Possible certified upper bound: {self._number(scale(report.possible_upper_bound))}",
            f"Possible limiting resource    : {report.possible_limiting_resource or '-'}",
            "",
            "IDEAL PROCESS / PERFECT MANIPULATORS",
            f"Nominal process ceiling       : {self._number(scale(report.ideal_process_nominal_throughput))}",
            f"Possible process ceiling      : {self._number(scale(report.ideal_process_possible_throughput))}",
            f"Nominal ideal hanger path     : {report.ideal_path_nominal_seconds:.1f} s",
            f"Possible ideal hanger path    : {report.ideal_path_possible_seconds:.1f} s",
            f"  residence / handling        : {report.ideal_path_details.get('nominal_residence_seconds', 0.0):.1f} / {report.ideal_path_details.get('nominal_handling_seconds', 0.0):.1f} s",
            f"Nominal ideal bottleneck      : {report.ideal_path_details.get('nominal_limiting_resource') or '-'}",
            f"Possible ideal bottleneck     : {report.ideal_path_details.get('possible_limiting_resource') or '-'}",
            "Meaning: every ideal stage cycle includes residence plus outbound lift,",
            "source drip, loaded travel and drop. A suitable manipulator is always",
            "immediately available; empty approach and all track conflicts are ignored.",
        ]
        if report.best_simulated_throughput is not None:
            lines += [
                f"Precise EventDriven           : {self._number(scale(report.best_simulated_throughput))}",
                f"  precise transports          : {report.best_simulated_throughput:.2f} transportów/h",
                f"Nominal gap                   : {self._number(scale(report.nominal_gap))}",
                f"Nominal relative gap          : {report.nominal_relative_gap_percent:.2f}%",
                f"Possible gap                  : {self._number(scale(report.possible_gap))}",
            ]
        lines += ["", "CERTIFIED NOMINAL RESOURCE BOUNDS"]
        for bound in report.nominal_bounds:
            if bound.certifying:
                lines.append(
                    f"- {bound.limiting_resource}: "
                    f"{self._number(scale(bound.throughput_per_hour))}"
                )
        lines += ["", "TRACK / ZONE DIAGNOSTICS (NOT CERTIFYING)"]
        for bound in report.nominal_diagnostics:
            lines.append(
                f"- {bound.limiting_resource}: "
                f"{self._number(scale(bound.throughput_per_hour))}"
            )
        lines += [
            "",
            "All capacity and gap values are production pieces per hour.",
            "Precise EventDriven uses physical HANGER_EXIT intervals, not the rounded",
            "steady-state window throughput.",
            "Assumptions: empty repositioning, exact YIELD timing and cyclic closure",
            "remain relaxed. Diagnostic interface bounds are not used to lower the",
            "certified upper bound.",
            "=" * 72,
        ]
        return "\n".join(lines)
