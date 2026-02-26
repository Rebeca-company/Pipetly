"""Utilities for safely parsing JSON from LLM responses.

The main pipeline now uses ``response_format={"type": "json_object"}`` via
OpenRouter (Native Structured Outputs), so the LLM returns clean JSON directly
and ``json.loads()`` is used inline.  ``extract_json`` is retained here as a
fallback helper for ad-hoc scripts or legacy code that does not send
``response_format``.
"""
from __future__ import annotations

import json
import re


def extract_json(text: str) -> dict:
    """
    Parse JSON from an LLM response that may be wrapped in markdown code fences.

    Fallback helper – prefer using ``response_format={"type": "json_object"}``
    in the request payload so the model returns clean JSON and plain
    ``json.loads()`` suffices.

    Handles:
    - Plain JSON
    - ```json ... ``` fences
    - ``` ... ``` fences
    """
    # Strip leading/trailing whitespace
    text = text.strip()

    # Remove markdown fences if present
    fence_match = re.search(r"```(?:json)?\s*([\s\S]+?)\s*```", text)
    if fence_match:
        text = fence_match.group(1).strip()

    # Find the outermost JSON object or array
    for start_char, end_char in [('{', '}'), ('[', ']')]:
        start = text.find(start_char)
        if start != -1:
            # Find matching closing bracket
            depth = 0
            for i, ch in enumerate(text[start:], start):
                if ch == start_char:
                    depth += 1
                elif ch == end_char:
                    depth -= 1
                    if depth == 0:
                        return json.loads(text[start: i + 1])

    # Last resort: parse the whole string
    return json.loads(text)
