from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QListWidget,
    QPlainTextEdit,
    QLabel,
    QSplitter
)

from PySide6.QtCore import (
    Qt
)

from PySide6.QtGui import QFontDatabase


class ReportsTab(QWidget):

    DEFAULT_SECTION = (
        "Log symulacji"
    )

    def __init__(
        self
    ):
        super().__init__()

        self.sections = {}

        self._build_ui()

    def _build_ui(
        self
    ):
        layout = QVBoxLayout()

        header = QHBoxLayout()

        self.title = QLabel(
            "Raporty z ostatniej symulacji"
        )

        header.addWidget(
            self.title
        )

        self.clear_button = QPushButton(
            "Wyczyść"
        )

        self.clear_button.clicked.connect(
            self.clear
        )

        header.addWidget(
            self.clear_button
        )

        layout.addLayout(
            header
        )

        splitter = QSplitter(
            Qt.Horizontal
        )

        self.report_list = QListWidget()

        self.report_list.currentTextChanged.connect(
            self._report_selected
        )

        splitter.addWidget(
            self.report_list
        )

        self.text = QPlainTextEdit()

        self.text.setReadOnly(
            True
        )
        self.text.setFont(
            QFontDatabase.systemFont(QFontDatabase.FixedFont)
        )

        self.text.setLineWrapMode(
            QPlainTextEdit.NoWrap
        )

        splitter.addWidget(
            self.text
        )

        splitter.setSizes(
            [250, 1200]
        )

        layout.addWidget(
            splitter
        )

        self.setLayout(
            layout
        )

    def _report_selected(
        self,
        report_name
    ):
        content = (
            self.sections.get(
                report_name,
                ""
            )
        )

        self.text.setPlainText(
            content
        )

    def _extract_sections(
        self,
        report_text
    ):
        sections = {
            self.DEFAULT_SECTION:
                report_text
        }

        lines = (
            report_text.splitlines()
        )

        current_name = None
        current_buffer = []

        def flush():
            nonlocal current_name
            nonlocal current_buffer

            if (
                current_name is None
            ):
                return

            sections[
                current_name
            ] = "\n".join(
                current_buffer
            ).strip()

        for index, line in enumerate(
            lines
        ):
            stripped = (
                line.strip()
            )

            if (
                stripped
                ==
                "THEORETICAL CAPACITY REPORT"
            ):
                flush()

                current_name = (
                    "Theoretical Capacity"
                )

                current_buffer = [
                    line
                ]

                continue

            if (
                stripped
                ==
                "LOAD TO UNLOAD LEAD TIME REPORT"
            ):
                flush()

                current_name = (
                    "Lead Time"
                )

                current_buffer = [
                    line
                ]

                continue

            if (
                stripped
                ==
                "EVENT DIAGNOSTICS"
            ):
                flush()

                current_name = (
                    "Event Diagnostics"
                )

                current_buffer = [
                    line
                ]

                continue

            if (
                stripped
                ==
                "QUEUE DIAGNOSTICS"
            ):
                flush()

                current_name = (
                    "Queue Diagnostics"
                )

                current_buffer = [
                    line
                ]

                continue

            if (
                stripped
                ==
                "PROCESS COMPLIANCE REPORT"
            ):
                flush()

                current_name = (
                    "Process Compliance"
                )

                current_buffer = [
                    line
                ]

                continue

            if (
                stripped
                ==
                "MANIPULATOR UTILIZATION REPORT"
            ):
                flush()

                current_name = (
                    "Manipulator Utilization"
                )

                current_buffer = [
                    line
                ]

                continue

            if (
                stripped
                ==
                "STATION RESIDENCE TIME REPORT"
            ):
                flush()

                current_name = (
                    "Station Residence"
                )

                current_buffer = [
                    line
                ]

                continue

            if (
                stripped
                ==
                "MANIPULATOR SEPARATION REPORT"
            ):
                flush()

                current_name = (
                    "Manipulator Separation"
                )

                current_buffer = [
                    line
                ]

                continue

            if (
                stripped
                ==
                "STATION RESERVATION SUMMARY"
            ):
                flush()

                current_name = (
                    "Station Reservations"
                )

                current_buffer = [
                    line
                ]

                continue

            if (
                current_name
                is not None
            ):
                current_buffer.append(
                    line
                )

        flush()

        return (
            sections
        )

    def show_report_text(
        self,
        report_text: str
    ):
        self.sections = (
            self._extract_sections(
                report_text
            )
        )

        self.report_list.clear()

        preferred_order = [
            "Theoretical Capacity",
            "Lead Time",
            "Event Diagnostics",
            "Queue Diagnostics",
            "Process Compliance",
            "Manipulator Utilization",
            "Station Residence",
            "Manipulator Separation",
            "Station Reservations",
            self.DEFAULT_SECTION
        ]

        for name in preferred_order:
            if (
                name
                in self.sections
            ):
                self.report_list.addItem(
                    name
                )

        for name in self.sections:
            if (
                self.report_list.findItems(
                    name,
                    Qt.MatchExactly
                )
            ):
                continue

            self.report_list.addItem(
                name
            )

        if (
            self.report_list.count()
            > 0
        ):
            self.report_list.setCurrentRow(
                0
            )

    def append_text(
        self,
        report_text: str
    ):
        current = (
            self.sections.get(
                self.DEFAULT_SECTION,
                ""
            )
        )

        current += (
            "\n"
            + report_text
        )

        self.show_report_text(
            current
        )

    def clear(
        self
    ):
        self.sections = {}

        self.report_list.clear()

        self.text.clear()