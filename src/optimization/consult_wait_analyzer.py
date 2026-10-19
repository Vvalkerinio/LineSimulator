class ConsultWaitAnalyzer:
    """Aggregate gross wait, productive preposition and true idle wait."""

    def summarize(self, plans):
        plans = list(plans)
        return {
            "consult_count": len(plans),
            "gross_consult_wait": sum(p.gross_consult_wait for p in plans),
            "productive_approach_time": sum(
                p.productive_approach_time for p in plans
            ),
            "net_idle_wait": sum(p.net_idle_wait for p in plans),
            "forced_process_bath_count": sum(
                1 for p in plans if p.forced_process_bath
            )
        }
