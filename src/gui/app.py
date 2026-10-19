import sys

from PySide6.QtWidgets import (
    QApplication
)

from main import config

from src.gui.main_window import (
    MainWindow
)


def main():

    app = QApplication(
        sys.argv
    )
    app.setApplicationName(
        "Line Simulator"
    )
    app.setApplicationDisplayName(
        "Line Simulator v1.0"
    )
    app.setApplicationVersion(
        "1.0.0"
    )
    app.setOrganizationName(
        "Electropoli"
    )

    window = MainWindow(
        config
    )

    window.show()

    sys.exit(
        app.exec()
    )


if __name__ == "__main__":
    main()