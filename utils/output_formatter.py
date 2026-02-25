"""Render the final Markdown report from scored protocols."""
from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from typing import List

from models.protocol import ScoredProtocol


def write_markdown_output(
    scored_protocols: List[ScoredProtocol],
    intent: str,
    output_dir: str = "output",
) -> Path:
    """
    Write a Markdown file containing the top-ranked protocols.

    Returns the path of the created file.
    """
    os.makedirs(output_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filepath = Path(output_dir) / f"protocols_{timestamp}.md"

    lines: list[str] = []
    lines.append(f"# Pipetly — Extracted Biomedical Protocols\n")
    lines.append(f"**Search intent:** {intent}\n")
    lines.append(f"**Generated:** {datetime.now().isoformat(timespec='seconds')}\n")
    lines.append("---\n")

    for rank, sp in enumerate(scored_protocols, start=1):
        p = sp.protocol
        lines.append(f"## Rank {rank} — {p.protocol_name}")
        lines.append(f"**Source:** {p.source_title}")
        if p.source_doi:
            lines.append(f"**DOI:** [{p.source_doi}](https://doi.org/{p.source_doi})")
        lines.append(f"**Relevance score:** {sp.score:.2f}")
        lines.append(f"**Scoring rationale:** {sp.reasoning}\n")

        lines.append("### Protocol Steps\n")
        for step in p.steps:
            lines.append(f"**Step {step.step_number}.** {step.description}")
            if step.reagents:
                lines.append(f"- *Reagents:* {', '.join(step.reagents)}")
            if step.equipment:
                lines.append(f"- *Equipment:* {', '.join(step.equipment)}")
            if step.duration:
                lines.append(f"- *Duration:* {step.duration}")
            if step.notes:
                lines.append(f"- *Notes:* {step.notes}")
            if step.citation_ref:
                lines.append(f"- *Citation:* {step.citation_ref}")
            lines.append("")

        lines.append("---\n")

    filepath.write_text("\n".join(lines), encoding="utf-8")
    return filepath
