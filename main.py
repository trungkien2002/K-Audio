"""K-Audio application entry point.

Entry point: Launches the PySide6 desktop application.
"""

import sys
import os

# Ensure the project root is on the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from app.theme import ThemeManager
from app.main_window import MainWindow


def patch_wheel_events():
    """Disable mouse wheel on QComboBox, QSlider, QSpinBox, QDoubleSpinBox
    to prevent accidental changes while scrolling.
    """
    try:
        from PySide6.QtWidgets import QComboBox, QSlider, QSpinBox, QDoubleSpinBox

        def ignore_wheel(self, event):
            event.ignore()

        QComboBox.wheelEvent = ignore_wheel
        QSlider.wheelEvent = ignore_wheel
        QSpinBox.wheelEvent = ignore_wheel
        QDoubleSpinBox.wheelEvent = ignore_wheel
    except ImportError:
        pass


def main():
    patch_wheel_events()

    app = QApplication(sys.argv)
    app.setApplicationName("K-Audio")
    app.setOrganizationName("K-Audio")
    app.setStyle("Fusion")
    app.setFont(QFont("Segoe UI", 10))

    # Apply dark theme
    app.setStyleSheet(ThemeManager.get_app_stylesheet())

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
