"""Final protocol formatting step.

Keeps the top protocols by relevance_score and writes a Markdown report for the
user. Protocol step wording is drafted by the LLM; metadata is composed in code.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, List, Optional

import httpx

from config import get_settings
from models.protocol import ExtractedProtocol, InheritedReference, ScoredProtocol

logger = logging.getLogger(__name__)
_s = get_settings()

_FORMAT_SYSTEM = """You are an expert scientific writer and protocol editor.
Your task is to transform dense, narrative scientific methodology text into a clear, chronological, and highly actionable numbered protocol.

You will receive:
1. The user's research intent.
2. The [Level 0] Primary Protocol text.
3. [Level N] Supplementary Protocol texts (if any). These are nested references where N indicates the depth of recursion (e.g., [Level 1] provides details missing in [Level 0]; [Level 2] provides details missing in [Level 1]).

Rules for Drafting the Output:
- Output strictly in Markdown format as a single numbered list (1., 2., 3., ...).
- **Resolve the Chain:** Follow the "Trigger Context" breadcrumbs. If [Level 0] cites a method detailed in [Level 1], and [Level 1] cites a specific buffer preparation detailed in [Level 2], you MUST unpack this chain and integrate all steps chronologically into the main flow.
- **Precision:** Retain all exact technical details (concentrations, volumes, times, temperatures, equipment).
- **No Hallucination:** Do not invent steps.
- **Citations:** Add inline citations for supplementarry protocols using [{doi}](https://doi.org/{doi})]. Place the citation at the end of the specific step it relates to.
"""

_FORMAT_SCHEMA: dict = {
    "name": "protocol_markdown_steps",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "steps_markdown": {"type": "string"}
        },
        "required": ["steps_markdown"],
        "additionalProperties": False,
    },
}


class ProtocolFormatter:
    """Select top protocols and generate final user-facing markdown output."""

    def __init__(self, max_concurrent_drafts: int = _s.llm_max_concurrent) -> None:
        self._base = _s.openrouter_base_url.rstrip("/")
        self._headers = {
            "Authorization": f"Bearer {_s.openrouter_api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/pipetly",
            "X-Title": "Pipetly",
        }
        self._draft_semaphore = asyncio.Semaphore(max_concurrent_drafts)
        self._http_client: Optional[httpx.AsyncClient] = None
        self._llm_token_events: list[dict[str, int | str]] = []
        self._llm_call_count = 0

    def get_llm_token_events(self) -> list[dict[str, int | str]]:
        """Return per-call token telemetry records for Step 9 formatting."""
        return list(self._llm_token_events)

    async def format_top_protocols(
        self,
        protocols: List[ExtractedProtocol],
    ) -> List[ScoredProtocol]:
        """Return Top-K protocols ordered by relevance_score."""
        packaged: list[ScoredProtocol] = []
        for protocol in protocols:
            score = float(protocol.relevance_score)
            packaged.append(
                ScoredProtocol(
                    protocol=protocol,
                    score=score,
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
        logger.info("Step 9 start - Final formatting on %d protocols.", len(protocols))
        self._llm_token_events.clear()
        self._llm_call_count = 0
        top_protocols = await self.format_top_protocols(protocols)

        out_dir = output_dir or _s.output_dir
        os.makedirs(out_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filepath = Path(out_dir) / f"protocols_{timestamp}.md"

        lines: list[str] = []
        lines.append("# Pipetly — Extracted Protocols\n")
        lines.append(f"**Search intent:** {intent}\n")
        lines.append(f"**Generated:** {datetime.now().isoformat(timespec='seconds')}\n")
        lines.append("---\n")

        self._http_client = httpx.AsyncClient(
            timeout=_s.http_timeout * 2,
            limits=httpx.Limits(max_keepalive_connections=20, max_connections=50),
        )

        try:
            draft_tasks = [
                self._draft_steps_with_semaphore(
                    sp.protocol.protocol_text,
                    intent,
                    sp.protocol.inherited_references,
                )
                for sp in top_protocols
            ]
            draft_results = await asyncio.gather(*draft_tasks, return_exceptions=True)
        finally:
            await self._http_client.aclose()
            self._http_client = None

        for rank, (sp, draft_result) in enumerate(zip(top_protocols, draft_results), start=1):
            p = sp.protocol
            lines.append(f"## Rank {rank} — Protocol")
            lines.append(f"**Source:** {p.source_title}")
            if p.source_doi:
                lines.append(f"\n**DOI:** [{p.source_doi}](https://doi.org/{p.source_doi})")
            lines.append(f"\n**Relevance score:** {sp.score:.1f}/100")
            lines.append("")

            if isinstance(draft_result, Exception):
                logger.warning(
                    "LLM step drafting failed for '%s'; using fallback: %s",
                    p.source_title[:100],
                    draft_result,
                )
                drafted_steps = "1. " + p.protocol_text.strip().replace("\n", " ")[:1000]
            else:
                drafted_steps = draft_result

            lines.append("### Protocol Steps\n")
            lines.append(drafted_steps)
            lines.append("")

            if p.inherited_references:
                lines.append("### Inherited References\n")
                lines.append("\nThese are references cited by this protocol that were resolved.")
                refs = []
                seen = set()
                for ref in p.inherited_references:
                    doi = (ref.target_doi or "").strip()
                    intent = (ref.search_intent or "").strip()
                    ctx = (ref.context_phrase or "").strip()
                    key = (ctx.lower(), doi.lower())
                    if doi and key not in seen:
                        seen.add(key)
                        refs.append((ctx, doi))
                if not refs:
                    lines.append("- None")
                else:
                    for ctx, doi in refs:
                        lines.append(f"- **{intent}**")
                        lines.append(f"\n  Extracted from: [{doi}](https://doi.org/{doi})")
                lines.append("")
                lines.append("---\n")

        filepath.write_text("\n".join(lines), encoding="utf-8")
        logger.info("Markdown report written to: %s", filepath)
        logger.info("Step 9 complete - Final report generated.")
        return filepath

    async def _draft_steps_with_semaphore(
        self,
        protocol_text: str,
        intent: str,
        inherited_references: List[InheritedReference],
    ) -> str:
        async with self._draft_semaphore:
            return await self._draft_steps_markdown(
                protocol_text,
                intent,
                inherited_references,
            )

    def _reference_citation(self, ref: InheritedReference) -> str:
        doi = (ref.target_doi or "").strip()
        if doi:
            return f"[DOI:{doi}]"

        title = (ref.target_title or ref.reference_text or "unknown reference").strip()
        year = f" ({ref.target_year})" if ref.target_year is not None else ""
        return f"[REF:{title}{year}]"

    async def _draft_steps_markdown(
        self,
        protocol_text: str,
        intent: str,
        inherited_references: List[InheritedReference],
    ) -> str:
        """Use LLM to rewrite protocol text into clear numbered markdown steps."""
        if not protocol_text.strip():
            return "1. (No protocol steps available)"

        nested_blocks: list[str] = []
        for ref in inherited_references:
            context = (ref.context_phrase or "").strip()
            resolved = (ref.resolved_fragment or "").strip()
            if not resolved:
                continue

            citation = self._reference_citation(ref)
            depth = getattr(ref, "resolution_depth", 1) or 1
            
            block = (
                f"### [Level {depth}] Supplementary Protocol\n"
                f"**Citation:** {citation}\n"
                f"**Trigger Context (Look for this phrase in Level {depth - 1}):** \"{context}\"\n"
                f"**Protocol Text:**\n{resolved}\n"
            )
            
            nested_blocks.append(block)

        nested_protocols_str = "\n\n".join(nested_blocks) if nested_blocks else "No supplementary nested protocols provided."
        user_prompt = (
            f"Research intent:\n{intent}\n\n"
            "Protocol source text:\n"
            f"{protocol_text}\n\n"
            "Inherited resolved fragments to integrate into steps (only when relevant):\n"
            f"{nested_protocols_str}"
        )
        payload: dict[str, Any] = {
            "model": _s.gemini_model_general,
            "messages": [
                {"role": "system", "content": _FORMAT_SYSTEM},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.0,
            "response_format": {"type": "json_schema", "json_schema": _FORMAT_SCHEMA},
        }

        try:
            if self._http_client is not None:
                resp = await self._http_client.post(
                    f"{self._base}/chat/completions",
                    json=payload,
                    headers=self._headers,
                )
            else:
                async with httpx.AsyncClient(timeout=_s.http_timeout * 2) as client:
                    resp = await client.post(
                        f"{self._base}/chat/completions",
                        json=payload,
                        headers=self._headers,
                    )

            if resp.is_error:
                logger.error("OpenRouter error %s – %s", resp.status_code, resp.text)
                resp.raise_for_status()
            raw_payload = resp.json()
            self._record_llm_usage(raw_payload)
            raw = raw_payload["choices"][0]["message"]["content"]
            data = json.loads(raw)
            md = data.get("steps_markdown", "").strip()
            return md or "1. (No protocol steps available)"
        except Exception as exc:  # noqa: BLE001
            logger.warning("LLM step drafting failed; using fallback: %s", exc)
            # Safe fallback to avoid empty output when LLM fails.
            return "1. " + protocol_text.strip().replace("\n", " ")[:1000]

    def _record_llm_usage(self, response_json: dict[str, Any]) -> None:
        usage = response_json.get("usage") or {}

        in_tokens = int(
            usage.get("prompt_tokens")
            or usage.get("input_tokens")
            or usage.get("promptTokens")
            or 0
        )
        out_tokens = int(
            usage.get("completion_tokens")
            or usage.get("output_tokens")
            or usage.get("completionTokens")
            or 0
        )
        total_tokens = int(usage.get("total_tokens") or (in_tokens + out_tokens))

        self._llm_call_count += 1
        event: dict[str, int | str] = {
            "step": "9",
            "call_index": self._llm_call_count,
            "input_tokens": in_tokens,
            "output_tokens": out_tokens,
            "total_tokens": total_tokens,
        }
        self._llm_token_events.append(event)

        logger.info(
            "LLM step 9 tokens (call %d) - in=%d out=%d total=%d",
            self._llm_call_count,
            in_tokens,
            out_tokens,
            total_tokens,
        )


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
        STEP8_FILE,
        load_model,
        load_model_list,
    )

    async def _main() -> None:
        print("[Step 9] START | Final Formatting and Output")
        intent = load_model(STEP1_FILE, ExpandedQuery).intent
        protocols = load_model_list(STEP8_FILE, ExtractedProtocol)
        formatter = ProtocolFormatter()
        top = await formatter.format_top_protocols(protocols)
        for item in top:
            print(f"  [{item.score:.1f}] {item.protocol.source_title[:70]}")
        md_path = await formatter.format_and_write(protocols, intent)
        print(
            f"[Step 9] DONE | candidates={len(protocols)} top_k={len(top)} | Output: {md_path}"
        )

    asyncio.run(_main())
