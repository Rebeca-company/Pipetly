"""Final protocol formatting step.

Keeps the top protocols by relevance_score and writes a Markdown report for the
user. Protocol step wording is drafted by the LLM; metadata is composed in code.
"""
from __future__ import annotations

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, List

import httpx

from config import get_settings
from models.protocol import ExtractedProtocol, InheritedReference, ScoredProtocol

logger = logging.getLogger(__name__)
_s = get_settings()

_FORMAT_SYSTEM = """You are a scientific writing assistant.
Transform protocol source text into concise, executable protocol steps.

Rules:
- Output in Markdown.
- Provide only a numbered list of steps (1., 2., 3., ...).
- Keep technical details (conditions, concentrations, temperatures, timings).
- Do not add inferred steps that are not in source text.
- Add inherited references as inline citations only where needed in the relevant step.
- Use inline format exactly: [DOI:10.xxxx/xxxxx]
- Do not invent citations or place citations in unrelated steps.
"""

_FORMAT_SCHEMA: dict = {
    "name": "protocol_markdown_steps",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "steps_markdown": {
                "type": "string",
                "description": "Numbered markdown steps only.",
            }
        },
        "required": ["steps_markdown"],
        "additionalProperties": False,
    },
}


class ProtocolFormatter:
    """Select top protocols and generate final user-facing markdown output."""

    def __init__(self) -> None:
        self._base = _s.openrouter_base_url.rstrip("/")
        self._headers = {
            "Authorization": f"Bearer {_s.openrouter_api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/pipetly",
            "X-Title": "Pipetly",
        }

    async def format_top_protocols(
        self,
        protocols: List[ExtractedProtocol],
        intent: str,
    ) -> List[ScoredProtocol]:
        """Return Top-K protocols ordered by relevance_score."""
        packaged: list[ScoredProtocol] = []
        for protocol in protocols:
            score = float(protocol.relevance_score)
            reason = (
                f"Selected by extractor relevance_score against intent: '{intent[:120]}'. "
                f"Resolved refs: {sum(1 for r in protocol.inherited_references if r.resolved_fragment)}"
                f"/{len(protocol.inherited_references)}."
            )
            packaged.append(
                ScoredProtocol(
                    protocol=protocol,
                    score=score,
                    reasoning=reason,
                )
            )

        packaged.sort(key=lambda sp: sp.score, reverse=True)
        top_k = packaged[: _s.top_k_protocols]
        logger.info("Packaged %d protocols; returning Top %d.", len(packaged), len(top_k))
        return top_k

    async def format_and_write(
        self,
        protocols: List[ExtractedProtocol],
        intent: str,
        output_dir: str | None = None,
    ) -> Path:
        """Select top protocols, draft steps with LLM, and write markdown report."""
        logger.info("Step 10 start - Final formatting on %d protocols.", len(protocols))
        top_protocols = await self.format_top_protocols(protocols, intent)

        out_dir = output_dir or _s.output_dir
        os.makedirs(out_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filepath = Path(out_dir) / f"protocols_{timestamp}.md"

        lines: list[str] = []
        lines.append("# Pipetly — Extracted Biomedical Protocols\n")
        lines.append(f"**Search intent:** {intent}\n")
        lines.append(f"**Generated:** {datetime.now().isoformat(timespec='seconds')}\n")
        lines.append("---\n")

        for rank, sp in enumerate(top_protocols, start=1):
            p = sp.protocol
            lines.append(f"## Rank {rank} — Protocol")
            lines.append(f"**Source:** {p.source_title}")
            if p.source_doi:
                lines.append(f"**DOI:** [{p.source_doi}](https://doi.org/{p.source_doi})")
            lines.append(f"**Relevance score:** {sp.score:.1f}/100")
            lines.append(f"**Selection rationale:** {sp.reasoning}\n")

            drafted_steps = await self._draft_steps_markdown(
                p.protocol_text,
                intent,
                p.inherited_references,
            )
            lines.append("### Protocol Steps\n")
            lines.append(drafted_steps)
            lines.append("")

            lines.append("### Inherited References\n")
            refs = []
            seen = set()
            for ref in p.inherited_references:
                doi = (ref.target_doi or "").strip()
                ctx = (ref.context_phrase or "").strip()
                key = (ctx.lower(), doi.lower())
                if doi and key not in seen:
                    seen.add(key)
                    refs.append((ctx, doi))
            if not refs:
                lines.append("- None")
            else:
                for ctx, doi in refs:
                    lines.append(f"- **Context:** {ctx}")
                    lines.append(f"  **Target DOI:** [{doi}](https://doi.org/{doi})")
            lines.append("")
            lines.append("---\n")

        filepath.write_text("\n".join(lines), encoding="utf-8")
        logger.info("Markdown report written to: %s", filepath)
        logger.info("Step 10 complete - Final report generated.")
        return filepath

    async def _draft_steps_markdown(
        self,
        protocol_text: str,
        intent: str,
        inherited_references: List[InheritedReference],
    ) -> str:
        """Use LLM to rewrite protocol text into clear numbered markdown steps."""
        if not protocol_text.strip():
            return "1. (No protocol steps available)"

        ref_lines = []
        for ref in inherited_references:
            doi = (ref.target_doi or "").strip()
            context = (ref.context_phrase or "").strip()
            if doi:
                ref_lines.append(f"- DOI: {doi} | Context: {context}")
        refs_block = "\n".join(ref_lines) if ref_lines else "- None"

        user_prompt = (
            f"Research intent:\n{intent}\n\n"
            "Protocol source text:\n"
            f"{protocol_text[:120_000]}\n\n"
            "Inherited references (use only if relevant to a step):\n"
            f"{refs_block}"
        )
        payload: dict[str, Any] = {
            "model": _s.gemini_model_general,
            "messages": [
                {"role": "system", "content": _FORMAT_SYSTEM},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.1,
            "response_format": {"type": "json_schema", "json_schema": _FORMAT_SCHEMA},
        }

        try:
            async with httpx.AsyncClient(timeout=_s.http_timeout * 2) as client:
                resp = await client.post(
                    f"{self._base}/chat/completions",
                    json=payload,
                    headers=self._headers,
                )
                if resp.is_error:
                    logger.error("OpenRouter error %s – %s", resp.status_code, resp.text)
                    resp.raise_for_status()
            raw = resp.json()["choices"][0]["message"]["content"]
            data = json.loads(raw)
            md = data.get("steps_markdown", "").strip()
            return md or "1. (No protocol steps available)"
        except Exception as exc:  # noqa: BLE001
            logger.warning("LLM step drafting failed; using fallback: %s", exc)
            # Safe fallback to avoid empty output when LLM fails.
            return "1. " + protocol_text.strip().replace("\n", " ")[:1000]


if __name__ == "__main__":
    import asyncio

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
        datefmt="%H:%M:%S",
    )

    from models.query import ExpandedQuery
    from utils.intermediate_io import (
        STEP1_FILE,
        STEP9_FILE,
        load_model,
        load_model_list,
    )

    async def _main() -> None:
        print("[Step 10] START | Final Formatting and Output")
        intent = load_model(STEP1_FILE, ExpandedQuery).intent
        protocols = load_model_list(STEP9_FILE, ExtractedProtocol)
        formatter = ProtocolFormatter()
        top = await formatter.format_top_protocols(protocols, intent)
        for item in top:
            print(f"  [{item.score:.1f}] {item.protocol.source_title[:70]}")
        md_path = await formatter.format_and_write(protocols, intent)
        print(
            f"[Step 10] DONE | candidates={len(protocols)} top_k={len(top)} | Output: {md_path}"
        )

    asyncio.run(_main())
