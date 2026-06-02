"""Application diagnostic logging."""

from __future__ import annotations

from datetime import datetime
import os
from pathlib import Path
import traceback


def log_root() -> Path:
    base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    path = base / "MF-LOG-ANALYZER-v2" / "logs"
    path.mkdir(parents=True, exist_ok=True)
    return path


def log_exception(exc: BaseException, *, context: str) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    path = log_root() / f"error-{timestamp}.log"
    details = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
    path.write_text(f"Context: {context}\n\n{details}", encoding="utf-8")
    return path
