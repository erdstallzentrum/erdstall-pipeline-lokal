from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QLabel,
    QProgressBar,
    QVBoxLayout,
    QWidget,
)

from config import BASE_DIR


class SplashScreen(QWidget):
    def __init__(self)-> None:
        super().__init__()

        self.setWindowTitle("Erdstall Admin")
        self.setFixedSize(500,300)
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint)
        self.setWindowFlag(Qt.WindowType.SplashScreen)

        self._build_ui()

    def _build_ui(self)->None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40,40,40,40)
        layout.setSpacing(20)
        layout.addStretch()

        self.logo_label = QLabel()
        self.logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        pixmap = QPixmap(str(BASE_DIR / "public" / "Logo.png"))

        if not pixmap.isNull():
            self.logo_label.setPixmap(
                pixmap.scaled(
                    220,
                    110,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
            )
        

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0,100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedHeight(14)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                background-color: #2b2b2b;
                border-radius: 4px;
            }

            QProgressBar::chunk {
                background-color: white;
                border-radius: 4px;
            }
            """)

        layout.addWidget(self.logo_label)
        layout.addWidget(self.progress_bar)
        layout.addStretch()
    