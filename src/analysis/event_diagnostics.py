from src.analysis.text_table_utils import format_text_table
from collections import Counter


class EventDiagnostics:

    def summarize(
        self,
        result
    ):

        counter = Counter()

        for event in result.events:

            counter[
                str(
                    event.event_type
                )
            ] += 1

        return counter

    def print_summary(
        self,
        result
    ):

        counter = (
            self.summarize(
                result
            )
        )

        print()
        print(
            "=" * 60
        )
        print(
            "EVENT DIAGNOSTICS"
        )
        print(
            "=" * 60
        )

        total = sum(
            counter.values()
        )

        print(
            f"Total events: {total}"
        )

        rows = []
        for event_name in sorted(counter.keys()):
            count = counter[event_name]
            percent = 100.0 * count / total if total else 0.0
            rows.append([str(event_name), str(count), f"{percent:.2f}%"])
        print(format_text_table(
            ["Event", "Count", "Share"], rows,
            ["left", "right", "right"]
        ))

        print(
            "=" * 60
        )