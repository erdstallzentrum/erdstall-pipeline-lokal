from __future__ import annotations

from pathlib import Path
from PySide6.QtCore import QSettings

class AppSettings:
    ORG = "Erdstall"
    APP = "Admin"

    @classmethod
    def settings(cls) -> QSettings:
        return QSettings(cls.ORG, cls.APP)
    
    @classmethod
    def get_fiji_exe(cls) -> Path | None:
        value = cls.settings().value("paths/fiji_exe", "")
        if not value:
            return None
        return Path(str(value)).expanduser()
    
    @classmethod
    def set_fiji_exe(cls, path: str | Path )-> None:
        cls.settings().setValue("paths/fiji_exe", str(path))