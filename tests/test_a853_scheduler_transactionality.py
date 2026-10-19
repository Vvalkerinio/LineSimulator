from pathlib import Path

def test_scheduler_transactionality_and_overlay():
 a=Path("src/core/assignment_selector.py").read_text(); e=Path("src/core/event_driven_simulator.py").read_text(); g=Path("src/gui/line_overview_tab.py").read_text()
 assert "commit_yield(proposal)" not in a[a.index("    def _find_best_assignment_for_manipulator"):a.index("    def _deadline_penalty")]
 assert "self.availability.reserve(best_assignment" not in a[a.index("    def select("):]
 for x in ("commit_selector_yield","PREDICTIVE_ADMISSION_BLOCKED","wake_by_resource=true"): assert x in e
 for x in ("_next_motion_target","_program_status_text","→ST","cons (M"): assert x in g
