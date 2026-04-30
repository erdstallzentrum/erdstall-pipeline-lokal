from __future__ import annotations
import sys
from pathlib import Path

import qdarktheme

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer
from PySide6.QtGui import QIcon
from erdstall_admin_gui.windows.splash_screen import SplashScreen
from erdstall_admin_gui.windows.main_window import MainWindow

def main() -> int:
    app = QApplication(sys.argv)
    BASE_DIR = Path(__file__).resolve().parent
    app.setWindowIcon(QIcon(str(BASE_DIR / "public" / "admin_icon.png")))
    qdarktheme.setup_theme("dark")

    splash = SplashScreen()
    splash.show()
    app.processEvents()

    main_window = MainWindow()

    progress_timer = QTimer()
    progress_value = {"value": 0}

    def update_progress() -> None:
        progress_value["value"] += 7
        splash.progress_bar.setValue(progress_value["value"])
        if progress_value["value"] >= 100:
            progress_timer.stop()
            splash.close()
            main_window.show()

    progress_timer.timeout.connect(update_progress)
    progress_timer.start(30)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())