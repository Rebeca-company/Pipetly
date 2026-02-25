"""Utilities for safely parsing JSON from LLM responses."""
from __future__ import annotations

import json
import re


def extract_json(text: str) -> dict:
    """
    Parse JSON from an LLM response that may be wrapped in markdown code fences.

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
