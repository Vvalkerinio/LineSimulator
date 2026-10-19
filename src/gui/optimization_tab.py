
from pathlib import Path

from PySide6.QtCore import QObject, QThread, Signal, Slot
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QFormLayout,
    QSpinBox, QPushButton, QProgressBar, QLabel, QTableWidget,
    QTableWidgetItem, QFileDialog, QMessageBox, QCheckBox, QComboBox
)

from src.optimization import OptimizationReport


class FunctionWorker(QObject):
    finished = Signal(object)
    failed = Signal(str)

    def __init__(self, function):
        super().__init__()
        self.function = function

    @Slot()
    def run(self):
        try:
            self.finished.emit(self.function())
        except Exception as exc:
            self.failed.emit(f"{type(exc).__name__}: {exc}")


class OptimizationWorker(QObject):
    progress = Signal(dict)
    finished = Signal(object)
    failed = Signal(str)

    def __init__(self, study_factory, candidate_factory):
        super().__init__()
        self.study_factory = study_factory
        self.candidate_factory = candidate_factory
        self._cancel = False

    def cancel_requested(self):
        return self._cancel

    @Slot()
    def cancel(self):
        self._cancel = True

    @Slot()
    def run(self):
        try:
            study = self.study_factory(
                progress_callback=self.progress.emit,
                cancel_requested=self.cancel_requested
            )
            result = study.run(self.candidate_factory())
            self.finished.emit(result)
        except Exception as exc:
            self.failed.emit(f"{type(exc).__name__}: {exc}")


class OptimizationTab(QWidget):
    """GUI shell for stage-5 optimization services.

    MainWindow injects two factories to avoid moving simulation logic into GUI:
    study_factory(progress_callback, cancel_requested) -> OptimizationStudy
    candidate_factory() -> iterable[OptimizationCandidate]
    """

    COLUMNS = (
        "LP", "Typ", "Status", "Start M1-M4", "Shared Bath",
        "Throughput / bound", "Transporty", "Zdarzenia", "Czas sym. [s]",
        "MIN violations", "MAX violations", "Deadlocki",
        "Powód odrzucenia"
    )

    def __init__(self, configuration, parent=None):
        super().__init__(parent)
        self.configuration = configuration
        self.study_factory = None
        self.candidate_factory = None
        self.prepare_callback = None
        self.evaluate_candidate_callback = None
        self.apply_result_callback = None
        self.restore_callback = None
        self.study_result = None
        self.thread = None
        self.worker = None
        self._build_ui()

    def set_factories(
        self,
        study_factory,
        candidate_factory,
        prepare_callback=None,
        evaluate_candidate_callback=None,
        apply_result_callback=None,
        restore_callback=None
    ):
        self.study_factory = study_factory
        self.candidate_factory = candidate_factory
        self.prepare_callback = prepare_callback
        self.evaluate_candidate_callback = evaluate_candidate_callback
        self.apply_result_callback = apply_result_callback
        self.restore_callback = restore_callback
        self.start_button.setEnabled(True)

    def _spin(self, minimum, maximum, value):
        widget = QSpinBox()
        widget.setRange(minimum, maximum)
        widget.setValue(value)
        return widget

    def _build_ui(self):
        layout = QVBoxLayout(self)
        settings_box = QGroupBox("Parametry badania")
        settings = QFormLayout(settings_box)
        self.optimization_mode = QComboBox()
        self.optimization_mode.addItem("Pełny EventDriven", "event")
        self.optimization_mode.addItem(
            "Theoretical screening → EventDriven finał", "theoretical"
        )
        self.screening_limit = self._spin(1, 1000000, 500)
        self.finalist_count = self._spin(1, 1000, 10)
        self.screening_cycles = self._spin(2, 100, 2)
        self.final_cycles = self._spin(2, 100, 8)
        self.use_cache = QCheckBox("Wznawiaj z cache")
        self.use_cache.setChecked(True)
        settings.addRow("Tryb optymalizacji:", self.optimization_mode)
        settings.addRow("Limit kandydatów:", self.screening_limit)
        settings.addRow("Liczba finalistów:", self.finalist_count)
        self.finalist_count_label = settings.labelForField(self.finalist_count)
        settings.addRow("Cykle screeningu:", self.screening_cycles)
        settings.addRow("Cykle finałowe:", self.final_cycles)
        settings.addRow("Cache:", self.use_cache)
        # EventDriven-only mode has no finalist or ProgramDriven cycle phase.
        for widget in (
            self.screening_cycles,
            self.final_cycles,
            self.use_cache
        ):
            widget.setVisible(False)
            label = settings.labelForField(widget)
            if label is not None:
                label.setVisible(False)
        layout.addWidget(settings_box)

        buttons = QHBoxLayout()
        self.start_button = QPushButton("Rozpocznij optymalizację")
        self.start_button.setEnabled(False)
        self.cancel_button = QPushButton("Przerwij po bieżącym kandydacie")
        self.cancel_button.setEnabled(False)
        self.export_csv_button = QPushButton("Eksportuj CSV")
        self.export_json_button = QPushButton("Eksportuj JSON")
        self.preview_button = QPushButton("Pokaż różnice")
        self.apply_button = QPushButton("Zastosuj wybrany wariant")
        self.restore_button = QPushButton("Cofnij zastosowany wariant")
        self.preview_button.setEnabled(False)
        self.apply_button.setEnabled(False)
        self.restore_button.setEnabled(False)
        self.export_csv_button.setEnabled(False)
        self.export_json_button.setEnabled(False)
        buttons.addWidget(self.start_button)
        buttons.addWidget(self.cancel_button)
        buttons.addStretch(1)
        buttons.addWidget(self.export_csv_button)
        buttons.addWidget(self.export_json_button)
        buttons.addWidget(self.preview_button)
        buttons.addWidget(self.apply_button)
        buttons.addWidget(self.restore_button)
        layout.addLayout(buttons)

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.status_label = QLabel("Gotowy. Wymagane są programy PLC i consulty.")
        layout.addWidget(self.progress)
        layout.addWidget(self.status_label)

        self.table = QTableWidget(0, len(self.COLUMNS))
        self.table.setHorizontalHeaderLabels(self.COLUMNS)
        self.table.setSortingEnabled(False)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        layout.addWidget(self.table, 1)

        self.start_button.clicked.connect(self.start)
        self.cancel_button.clicked.connect(self.cancel)
        self.export_csv_button.clicked.connect(self.export_csv)
        self.export_json_button.clicked.connect(self.export_json)
        self.preview_button.clicked.connect(self.preview_selected)
        self.apply_button.clicked.connect(self.apply_selected)
        self.restore_button.clicked.connect(self.restore_applied)
        self.table.itemSelectionChanged.connect(self._selection_changed)
        self.optimization_mode.currentIndexChanged.connect(
            self._optimization_mode_changed
        )
        self._optimization_mode_changed()

    def _optimization_mode_changed(self):
        theoretical = self.optimization_mode.currentData() == "theoretical"
        self.finalist_count.setVisible(theoretical)
        self.finalist_count.setEnabled(theoretical)
        if self.finalist_count_label is not None:
            self.finalist_count_label.setVisible(theoretical)
        if theoretical and self.screening_limit.value() == 500:
            self.screening_limit.setValue(5000)
            self.finalist_count.setValue(20)
        elif not theoretical and self.screening_limit.value() == 5000:
            self.screening_limit.setValue(500)

    def _settings_payload(self):
        return {
            "optimization_mode": self.optimization_mode.currentData(),
            "screening_limit": self.screening_limit.value(),
            "finalist_count": self.finalist_count.value(),
            "screening_cycles": self.screening_cycles.value(),
            "final_cycles": self.final_cycles.value(),
            "use_cache": self.use_cache.isChecked()
        }

    @Slot()
    def start(self):
        if self.study_factory is None or self.candidate_factory is None:
            QMessageBox.warning(self, "Optymalizacja", "Brak kontekstu programu PLC.")
            return
        if self.prepare_callback is not None:
            self.prepare_callback()
        self.start_button.setEnabled(False)
        self.cancel_button.setEnabled(True)
        self.export_csv_button.setEnabled(False)
        self.export_json_button.setEnabled(False)
        self.table.setRowCount(0)
        self.progress.setValue(0)
        payload = self._settings_payload()

        def bound_study_factory(progress_callback, cancel_requested):
            return self.study_factory(
                payload, progress_callback, cancel_requested
            )

        self.thread = QThread(self)
        self.worker = OptimizationWorker(bound_study_factory, self.candidate_factory)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.progress.connect(self.on_progress)
        self.worker.finished.connect(self.on_finished)
        self.worker.failed.connect(self.on_failed)
        self.worker.finished.connect(self.thread.quit)
        self.worker.failed.connect(self.thread.quit)
        self.thread.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.thread.start()

    @Slot()
    def cancel(self):
        if self.worker is not None:
            self.worker.cancel()
            self.status_label.setText("Kończenie bieżącego kandydata...")
            self.cancel_button.setEnabled(False)

    @Slot(dict)
    def on_progress(self, event):
        completed = int(event.get("completed", 0))
        total = max(1, int(event.get("total", 1)))
        self.progress.setValue(round(completed * 100 / total))
        phase = event.get("phase", "")
        cached = " | cache" if event.get("cache_hit") else ""
        result = event.get("result")
        best_text = ""
        if result is not None:
            cycle = result.metrics.get("program_cycle_time")
            theoretical = result.metrics.get("theoretical_possible_upper_bound")
            throughput = result.metrics.get("event_throughput_per_hour")
            if throughput not in (None, ""):
                best_text = f" | Event={float(throughput):.3f}/h"
            elif theoretical not in (None, ""):
                best_text = f" | UB={float(theoretical):.3f}/h"
            elif cycle not in (None, ""):
                best_text = f" | cycle={float(cycle):.1f}s"
        self.status_label.setText(
            f"{phase}: {completed}/{total}{cached}{best_text}"
        )

    @Slot(object)
    def on_finished(self, result):
        self.study_result = result
        self._show_ranking(result.ranking)
        theoretical_count = int(getattr(result, "theoretical_evaluations", 0))
        event_count = int(getattr(result, "event_evaluations", 0))
        if theoretical_count:
            status_text = (
                f"Zakończono. Screening theoretical: {theoretical_count}, "
                f"EventDriven finaliści: {event_count}, "
                f"odrzucone: {result.rejected_candidates}"
            )
        else:
            status_text = (
                f"Zakończono. Kandydaci: {result.evaluated_candidates}, "
                f"referencja: {len(result.reference_results)}, "
                f"odrzucone kandydaty: {result.rejected_candidates}"
            )
        self.status_label.setText(status_text)
        self.progress.setValue(100)
        self.start_button.setEnabled(True)
        self.cancel_button.setEnabled(False)
        self.export_csv_button.setEnabled(bool(result.ranking))
        self.export_json_button.setEnabled(bool(result.ranking))
        self._selection_changed()

    @Slot(str)
    def on_failed(self, message):
        self.status_label.setText("Błąd optymalizacji")
        QMessageBox.critical(self, "Optymalizacja", message)
        self.start_button.setEnabled(True)
        self.cancel_button.setEnabled(False)

    def _show_ranking(self, ranking):
        self.table.setRowCount(len(ranking))
        for row, result in enumerate(ranking):
            metrics = result.metrics
            values = (
                row + 1,
                metrics.get("candidate_type", "EVENT_CANDIDATE"),
                result.status,
                "-".join(map(str, result.candidate.start_positions)),
                "; ".join(
                    f"{item.group_name}:{item.mode}={item.value:g}"
                    for item in getattr(
                        result.candidate, "shared_bath_parameters", ()
                    )
                ),
                (
                    metrics.get("event_throughput_per_hour")
                    if metrics.get("event_throughput_per_hour") not in (None, "")
                    else (
                        f"UB {float(metrics['theoretical_possible_upper_bound']):.3f}"
                        if metrics.get("theoretical_possible_upper_bound") not in (None, "")
                        else ""
                    )
                ),
                metrics.get("event_completed_transports", ""),
                metrics.get("event_processed_events", ""),
                metrics.get("event_final_time", ""),
                metrics.get("event_min_residence_failures", ""),
                metrics.get("event_max_residence_failures", ""),
                metrics.get("event_deadlock_count", ""),
                "; ".join(result.rejection_reasons)
            )
            for column, value in enumerate(values):
                self.table.setItem(row, column, QTableWidgetItem(str(value)))

    def _selected_result(self):
        if self.study_result is None:
            return None
        row = self.table.currentRow()
        ranking = self.study_result.ranking
        if not 0 <= row < len(ranking):
            return None
        return ranking[row]

    @Slot()
    def _selection_changed(self):
        selected = self._selected_result()
        valid = (
            selected is not None and selected.status == "VALID"
            and selected.metrics.get("candidate_type") == "EVENT_CANDIDATE"
        )
        self.preview_button.setEnabled(selected is not None)
        self.apply_button.setEnabled(
            valid and self.evaluate_candidate_callback is not None
            and self.apply_result_callback is not None
        )

    @Slot()
    def preview_selected(self):
        result = self._selected_result()
        if result is None:
            return
        metrics = result.metrics
        screening = metrics.get("screening")
        lines = [
            f"Status: {result.status}",
            f"Start M1-M4: {result.candidate.start_positions}",
            "Shared Bath: " + "; ".join(
                f"{item.group_name}:{item.mode}={item.value:g}"
                for item in getattr(result.candidate, "shared_bath_parameters", ())
            ),
            f"Cycle time: {metrics.get('program_cycle_time', '')}",
            f"Typ oceny: {metrics.get('evaluation_phase', metrics.get('candidate_type', ''))}",
            f"Event throughput/h (inter-exit): {metrics.get('event_throughput_per_hour', '')}",
            f"Theoretical nominal upper bound/h: {metrics.get('theoretical_nominal_upper_bound', '')}",
            f"Theoretical possible upper bound/h: {metrics.get('theoretical_possible_upper_bound', '')}",
            f"Theoretical bottleneck: {metrics.get('theoretical_limiting_resource', '')}",
            f"Startup access [s]: {metrics.get('theoretical_startup_access_seconds', '')}",
            f"Shared Bath proxy penalty: {metrics.get('theoretical_shared_bath_penalty', '')}",
            f"Start spacing margin: {metrics.get('theoretical_start_spacing_margin', '')}",
            f"Theoretical rank: {metrics.get('theoretical_rank', '')}",
            f"Window throughput/h: {metrics.get('windowed_steady_throughput_per_hour', '')}",
            f"Średni odstęp wyjść [s]: {metrics.get('mean_exit_interval', '')}",
            f"Wyjścia w analizie: {metrics.get('throughput_exit_count', '')}",
            f"CV odstępów: {metrics.get('exit_interval_cv', '')}",
            f"Program throughput/h: {metrics.get('program_throughput_per_hour', '')}",
            f"Realization ratio: {metrics.get('throughput_realization_ratio', '')}",
            f"Consult wait: {metrics.get('gross_consult_wait', '')}",
            f"Track wait: {metrics.get('track_wait', '')}",
            f"Parking nad procesem: {metrics.get('process_bath_idle_time', '')}",
            f"Puste przejazdy: {metrics.get('empty_travel_time', '')}",
            f"Powody odrzucenia: {'; '.join(result.rejection_reasons) or 'brak'}"
        ]
        if screening is not None:
            lines.append(
                f"Screening cycle: {screening.metrics.get('program_cycle_time', '')}"
            )
        QMessageBox.information(
            self, "Różnice wariantu", "\n".join(lines)
        )

    @Slot()
    def apply_selected(self):
        selected = self._selected_result()
        if selected is None or selected.status != "VALID":
            return
        answer = QMessageBox.question(
            self,
            "Zastosuj wariant",
            "Wybrany wariant zostanie ponownie przeliczony EventDriven. "
            "Po poprawnej walidacji zastosowane zostaną pozycje startowe "
            "M1-M4 oraz ustawienia Shared Bath. Program PLC i consulty nie "
            "zostaną zmienione. Kontynuować?"
        )
        if answer != QMessageBox.Yes:
            return
        self.apply_button.setEnabled(False)
        self.status_label.setText("Końcowa walidacja wybranego wariantu...")
        self.application_thread = QThread(self)
        self.application_worker = FunctionWorker(
            lambda: self.evaluate_candidate_callback(selected.candidate)
        )
        self.application_worker.moveToThread(self.application_thread)
        self.application_thread.started.connect(self.application_worker.run)
        self.application_worker.finished.connect(self._application_ready)
        self.application_worker.failed.connect(self.on_failed)
        self.application_worker.finished.connect(self.application_thread.quit)
        self.application_worker.failed.connect(self.application_thread.quit)
        self.application_thread.finished.connect(
            self.application_worker.deleteLater
        )
        self.application_thread.finished.connect(
            self.application_thread.deleteLater
        )
        self.application_thread.start()

    @Slot(object)
    def _application_ready(self, result):
        if result.status != "VALID":
            QMessageBox.critical(
                self, "Zastosuj wariant",
                "Końcowa walidacja odrzuciła wariant:\n" +
                "\n".join(result.rejection_reasons)
            )
            self._selection_changed()
            return
        self.apply_result_callback(result)
        self.status_label.setText("Zastosowano konfigurację EventDriven.")
        self.restore_button.setEnabled(self.restore_callback is not None)
        QMessageBox.information(
            self, "Zastosuj wariant",
            "Zastosowano pozycje startowe M1-M4 oraz ustawienia Shared Bath. "
            "Program PLC i consulty pozostały bez zmian."
        )
        self._selection_changed()

    @Slot()
    def restore_applied(self):
        if self.restore_callback is None:
            return
        self.restore_callback()
        self.restore_button.setEnabled(False)
        self.status_label.setText("Przywrócono konfigurację sprzed zastosowania wariantu.")

    def _choose_export_path(self, suffix):
        path, _ = QFileDialog.getSaveFileName(
            self, "Eksport wyników optymalizacji", "optimization_results" + suffix,
            "CSV (*.csv)" if suffix == ".csv" else "JSON (*.json)"
        )
        return Path(path) if path else None

    @Slot()
    def export_csv(self):
        path = self._choose_export_path(".csv")
        if path and self.study_result:
            OptimizationReport().write_csv(path, self.study_result)

    @Slot()
    def export_json(self):
        path = self._choose_export_path(".json")
        if path and self.study_result:
            OptimizationReport().write_json(path, self.study_result)
