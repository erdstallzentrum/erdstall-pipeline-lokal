from PySide6.QtCore import Signal
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout


class ProjectListItemWidget(QWidget):
    delete_requested = Signal(str)
    selected = Signal(str)

    def __init__(self, project_name: str)-> None:
        super().__init__()
        self.project_name = project_name

        self.name_label = QLabel(project_name)

        self.delete_button = QPushButton()
        self.delete_button.setToolTip(f"Delete {project_name}")
        self.delete_button.setFixedSize(32,32)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8,4,8,4)
        layout.addWidget(self.name_label)
        layout.addStretch()
        layout.addWidget(self.delete_button)

        self.delete_button.clicked.connect(self._on_delete_clicked)

    def _on_delete_clicked(self) ->None:
        self.delete_requested.emit(self.project_name)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if self.delete_button.geometry().contains(event.pos()):
            return
        self.selected.emit(self.project_name)
        super().mousePressEvent(event)