from PySide6.QtCore import Qt

from PySide6.QtGui import (
    QColor,
    QBrush,
    QPen
)

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QGraphicsView,
    QGraphicsScene,
    QGraphicsRectItem,
    QGraphicsSimpleTextItem
)


class GanttTab(QWidget):

    ROW_HEIGHT = 40

    BAR_HEIGHT = 28

    LEFT_MARGIN = 140

    TOP_MARGIN = 50

    TIME_SCALE = 4

    LEGEND_X = 30

    LEGEND_Y = 10

    def __init__(
        self
    ):
        super().__init__()

        layout = QVBoxLayout()

        self.scene = QGraphicsScene()

        self.view = QGraphicsView(
            self.scene
        )

        self.view.setDragMode(
            QGraphicsView.ScrollHandDrag
        )

        layout.addWidget(
            self.view
        )

        self.setLayout(
            layout
        )

    #
    # Kolor wg obszaru linii
    #
    def station_color(
        self,
        station_id: int
    ) -> QColor:

        if station_id <= 5:
            return QColor("#4e79a7")

        if station_id <= 10:
            return QColor("#59a14f")

        if station_id <= 15:
            return QColor("#edc948")

        if station_id <= 20:
            return QColor("#f28e2b")

        return QColor("#e15759")

    def draw_legend(
        self
    ):

        legend = [
            ("S1-S5", "#4e79a7"),
            ("S6-S10", "#59a14f"),
            ("S11-S15", "#edc948"),
            ("S16-S20", "#f28e2b"),
            ("S21-S22", "#e15759")
        ]

        y = self.LEGEND_Y

        for text, color in legend:

            rect = QGraphicsRectItem(
                self.LEGEND_X,
                y,
                20,
                20
            )

            rect.setBrush(
                QBrush(
                    QColor(color)
                )
            )

            self.scene.addItem(
                rect
            )

            label = (
                QGraphicsSimpleTextItem(
                    text
                )
            )

            label.setPos(
                self.LEGEND_X + 30,
                y
            )

            self.scene.addItem(
                label
            )

            y += 25

    def update_result(
        self,
        result
    ):

        self.scene.clear()

        tasks = sorted(
            result.manipulator_tasks,
            key=lambda t: (
                t.manipulator_id,
                t.start_time
            )
        )

        if not tasks:
            return

        self.draw_legend()

        manipulators = sorted(
            {
                task.manipulator_id
                for task
                in tasks
            }
        )

        row_map = {
            manipulator_id: index
            for index, manipulator_id
            in enumerate(
                manipulators
            )
        }

        #
        # Opisy manipulatorów
        #
        for manipulator_id in manipulators:

            row = row_map[
                manipulator_id
            ]

            y = (
                self.TOP_MARGIN
                + row * self.ROW_HEIGHT
            )

            text = (
                QGraphicsSimpleTextItem(
                    f"M{manipulator_id}"
                )
            )

            text.setPos(
                20,
                y
            )

            self.scene.addItem(
                text
            )

        #
        # Zadania
        #
        for task in tasks:

            row = row_map[
                task.manipulator_id
            ]

            x = (
                self.LEFT_MARGIN
                + task.start_time
                * self.TIME_SCALE
            )

            y = (
                self.TOP_MARGIN
                + row * self.ROW_HEIGHT
            )

            duration = (
                task.end_time
                - task.start_time
            )

            width = max(
                8,
                duration
                * self.TIME_SCALE
            )

            color = (
                self.station_color(
                    task.target_station
                )
            )

            rect = (
                QGraphicsRectItem(
                    x,
                    y,
                    width,
                    self.BAR_HEIGHT
                )
            )

            rect.setBrush(
                QBrush(color)
            )

            rect.setPen(
                QPen(Qt.black)
            )

            rect.setToolTip(
                (
                    f"Hanger: "
                    f"{task.hanger_id}\n"
                    f"Manipulator: "
                    f"{task.manipulator_id}\n"
                    f"Transport: "
                    f"{task.source_station}"
                    f" -> "
                    f"{task.target_station}\n"
                    f"Start: "
                    f"{task.start_time:.2f}\n"
                    f"End: "
                    f"{task.end_time:.2f}\n"
                    f"Duration: "
                    f"{duration:.2f}"
                )
            )

            self.scene.addItem(
                rect
            )

            #
            # Opis transportu
            #
            label = (
                QGraphicsSimpleTextItem(
                    f"{task.source_station}"
                    f"→"
                    f"{task.target_station}"
                )
            )

            label.setPos(
                x + 2,
                y + 2
            )

            self.scene.addItem(
                label
            )

        #
        # Oś czasu
        #
        max_time = max(
            task.end_time
            for task
            in tasks
        )

        tick_step = max(
            50,
            int(max_time / 20)
        )

        tick = 0

        while tick <= max_time:

            x = (
                self.LEFT_MARGIN
                + tick
                * self.TIME_SCALE
            )

            line = self.scene.addLine(
                x,
                self.TOP_MARGIN - 20,
                x,
                self.TOP_MARGIN
                +
                (
                    len(manipulators)
                    + 2
                )
                * self.ROW_HEIGHT
            )

            line.setPen(
                QPen(
                    QColor("#D0D0D0")
                )
            )

            text = (
                QGraphicsSimpleTextItem(
                    str(
                        int(tick)
                    )
                )
            )

            text.setPos(
                x,
                self.TOP_MARGIN - 35
            )

            self.scene.addItem(
                text
            )

            tick += tick_step

        #
        # Nagłówek
        #
        header = (
            QGraphicsSimpleTextItem(
                "Wykres Gantta Manipulatorów"
            )
        )

        header.setPos(
            self.LEFT_MARGIN,
            10
        )

        self.scene.addItem(
            header
        )

        self.scene.setSceneRect(
            self.scene.itemsBoundingRect()
        )