from __future__ import annotations
import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer
from erdstall_admin_gui.windows.main_window import MainWindow
from erdstall_admin_gui.windows.splash_screen import SplashScreen
from PySide6.QtGui import QIcon


def main() -> int:
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon("public/admin_icon.png"))

    splash = SplashScreen()
    splash.show()

    main_window = MainWindow()

    progress_timer = QTimer()
    progress_value = {"value": 0}

    def update_progress()-> None:
        progress_value["value"] += 9
        splash.progress_bar.setValue(progress_value["value"])
        if progress_value["value"] >=100:
            progress_timer.stop()
            splash.close()
            main_window.show()
    
    progress_timer.timeout.connect(update_progress)
    progress_timer.start(90)

    return app.exec()


if __name__  == "__main__":
    main()