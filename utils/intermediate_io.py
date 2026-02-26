"""Centralized utilities for reading/writing intermediate pipeline outputs.

Every pipeline step can save its output here so that subsequent steps can
load it directly when run as stand-alone scripts.

Directory layout::

    <project_root>/
        intermediate_outputs/
            step1_expanded_query.json
            step2_raw_papers.json
            step3_filtered_papers.json
            step4_protocols.json
            step5_scored_protocols.json

Usage example (saving)::

    from utils.intermediate_io import save_json, STEP1_FILE
    save_json(expanded_query, STEP1_FILE)

Usage example (loading)::

    from utils.intermediate_io import load_model, STEP1_FILE
    from models.query import ExpandedQuery
    expanded = load_model(STEP1_FILE, ExpandedQuery)
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, List, Type, TypeVar

from pydantic import BaseModel

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Directory – resolved relative to this file so it works regardless of the
# working directory the script is invoked from.
# ---------------------------------------------------------------------------
INTERMEDIATE_DIR: Path = Path(__file__).resolve().parent.parent / "intermediate_outputs"

# ---------------------------------------------------------------------------
# Well-known filenames for each pipeline step
# ---------------------------------------------------------------------------
STEP1_FILE = "step1_expanded_query.json"
STEP2_FILE = "step2_raw_papers.json"
STEP3_FILE = "step3_filtered_papers.json"
STEP4_FILE = "step4_protocols.json"
STEP5_FILE = "step5_scored_protocols.json"


# ---------------------------------------------------------------------------
# Core helpers
# ---------------------------------------------------------------------------

def ensure_intermediate_dir() -> Path:
    """Create ``intermediate_outputs/`` if it does not exist and return its path."""
    INTERMEDIATE_DIR.mkdir(parents=True, exist_ok=True)
    return INTERMEDIATE_DIR


def save_json(data: Any, filename: str) -> Path:
    """Serialise *data* and write it to ``intermediate_outputs/<filename>``.

    *data* may be:

    * A single Pydantic :class:`~pydantic.BaseModel` instance.
    * A list of Pydantic models (each serialised via ``model_dump()``).
    * Any plain JSON-serialisable value (dict, list, str, …).

    Returns the :class:`~pathlib.Path` of the written file.
    """
    ensure_intermediate_dir()
    path = INTERMEDIATE_DIR / filename

    if isinstance(data, list):
        serialised: Any = [
            item.model_dump() if isinstance(item, BaseModel) else item
            for item in data
        ]
    elif isinstance(data, BaseModel):
        serialised = data.model_dump()
    else:
        serialised = data

    path.write_text(json.dumps(serialised, indent=2, ensure_ascii=False), encoding="utf-8")
    logger.info("Intermediate output saved → %s", path)
    return path


T = TypeVar("T", bound=BaseModel)


def load_model(filename: str, model: Type[T]) -> T:
    """Load and validate a single Pydantic model from ``intermediate_outputs/<filename>``.

    Raises :class:`FileNotFoundError` with a helpful message when the file is
    missing (i.e. the previous step has not been run yet).
    """
    path = _require_file(filename)
    return model.model_validate(json.loads(path.read_text(encoding="utf-8")))


def load_model_list(filename: str, model: Type[T]) -> List[T]:
    """Load and validate a list of Pydantic models from ``intermediate_outputs/<filename>``.

    Raises :class:`FileNotFoundError` with a helpful message when the file is
    missing (i.e. the previous step has not been run yet).
    """
    path = _require_file(filename)
    raw: list[dict] = json.loads(path.read_text(encoding="utf-8"))
    return [model.model_validate(item) for item in raw]


# ---------------------------------------------------------------------------
# Internal
# ---------------------------------------------------------------------------

def _require_file(filename: str) -> Path:
    """Return ``intermediate_outputs/<filename>`` or raise :class:`FileNotFoundError`."""
    path = INTERMEDIATE_DIR / filename
    if not path.exists():
        raise FileNotFoundError(
            f"Required intermediate file not found: {path}\n"
            f"Please run the preceding pipeline step first."
        )
    return path
