"""Logging utilities for Pipetly."""

import logging
from pathlib import Path

from config import get_settings

_current_file_handler: logging.FileHandler | None = None
# intermediate_outputs is resolved relative to config.py location
INTERMEDIATE_DIR: Path = Path(__file__).resolve().parent.parent / "intermediate_outputs"


def setup_logging() -> None:
    """Configure a standard root logger for Pipetly based on config level."""
    try:
        settings = get_settings()
        level_name = settings.log_level.upper()
        level = getattr(logging, level_name, logging.INFO)
    except Exception:
        level = logging.INFO

    root = logging.getLogger()
    if not root.handlers:
        console = logging.StreamHandler()
        console.setLevel(level)
        formatter = logging.Formatter(
            fmt="%(asctime)s [%(levelname)s] %(name)s – %(message)s",
            datefmt="%H:%M:%S",
        )
        console.setFormatter(formatter)
        root.addHandler(console)
        root.setLevel(level)


def set_stage_logger(stage_name: str | None) -> None:
    """Redirect stage/step logs to a dedicated log file if enabled."""
    global _current_file_handler
    
    try:
        settings = get_settings()
        if not settings.export_stage_logs:
            return
    except Exception:
        # Fallback if settings validation fails during boot/tests
        pass

    root = logging.getLogger()

    # Remove existing handler
    if _current_file_handler is not None:
        root.removeHandler(_current_file_handler)
        _current_file_handler.close()
        _current_file_handler = None

    if not stage_name:
        return

    # Ensure logs folder exists
    log_dir = INTERMEDIATE_DIR / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / f"{stage_name}.log"

    # Set up and append FileHandler
    try:
        handler = logging.FileHandler(log_file, mode="w", encoding="utf-8")
        handler.setLevel(root.level or logging.INFO)
        formatter = logging.Formatter(
            fmt="%(asctime)s [%(levelname)s] %(name)s – %(message)s",
            datefmt="%H:%M:%S",
        )
        handler.setFormatter(formatter)
        root.addHandler(handler)
        _current_file_handler = handler
    except Exception as exc:
        # Fallback logging error to console
        logging.getLogger("utils.logger").warning(
            "Failed to initialize stage file logging: %s", exc
        )
