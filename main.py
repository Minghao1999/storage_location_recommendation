import sys
from PySide6.QtWidgets import QApplication, QWidget, QPushButton, QVBoxLayout

from heatmap_qt import run_heatmap_qt
from gdrive.gdrive_loader import download_daily_files


class MainWindow(QWidget):

    def __init__(self):
        super().__init__()

        self.setWindowTitle("Warehouse Heatmap Tool")
        self.resize(300,150)

        self.heatmap_window = None

        layout = QVBoxLayout()

        btn = QPushButton("Open Heatmap")
        btn.clicked.connect(self.open_heatmap)

        layout.addWidget(btn)

        self.setLayout(layout)

    def open_heatmap(self):

        inventory_file, empty_file = download_daily_files()

        self.heatmap_window = run_heatmap_qt(inventory_file, empty_file)


if __name__ == "__main__":

    app = QApplication(sys.argv)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())