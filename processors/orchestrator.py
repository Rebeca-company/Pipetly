"""Module 2 – Multi-Source API Orchestrator.

Fans out search queries across all configured API clients, collects metadata,
and attempts to retrieve full text for each paper.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Dict, List

from config import get_settings
from models.paper import FullText, FullTextFormat, Paper
from models.query import ExpandedQuery
from api_clients import (
    CrossRefClient,
    ElsevierClient,
    EuropePMCClient,
    OpenAlexClient,
    SemanticScholarClient,
)

logger = logging.getLogger(__name__)
_s = get_settings()


class MultiSourceOrchestrator:
    """Fan out queries to all sources and aggregate results."""

    async def fetch_papers(self, expanded_query: ExpandedQuery) -> List[Paper]:
        """
        Search every API with the keyword queries, collect metadata,
        then attempt to fetch full text for each unique paper.
        """
        all_papers: list[Paper] = []

        async with (
            EuropePMCClient() as epmc,
            SemanticScholarClient() as s2,
            ElsevierClient() as els,
            CrossRefClient() as cr,
            OpenAlexClient() as oa,
        ):
            # ── Phase 1: metadata search ──────────────────────────────────────
            search_tasks = []
            clients_labels = []
            for q in expanded_query.keyword_queries:
                search_tasks.append(epmc.search(q, _s.max_papers_per_source))
                clients_labels.append(f"europe_pmc|{q[:40]}")
                search_tasks.append(s2.search(q, _s.max_papers_per_source))
                clients_labels.append(f"semantic_scholar|{q[:40]}")
                search_tasks.append(els.search(q, _s.max_papers_per_source))
                clients_labels.append(f"elsevier|{q[:40]}")
                search_tasks.append(cr.search(q, _s.max_papers_per_source))
                clients_labels.append(f"crossref|{q[:40]}")
                search_tasks.append(oa.search(q, _s.max_papers_per_source))
                clients_labels.append(f"openalex|{q[:40]}")

            results = await asyncio.gather(*search_tasks, return_exceptions=True)
            for label, result in zip(clients_labels, results):
                if isinstance(result, Exception):
                    logger.warning("Search error [%s]: %s", label, result)
                else:
                    all_papers.extend(result)  # type: ignore[arg-type]

            # ── Phase 2: full-text retrieval ──────────────────────────────────
            # Map client instance to its papers for targeted fetch
            client_map: Dict[str, object] = {
                "europe_pmc": epmc,
                "semantic_scholar": s2,
                "elsevier": els,
                "crossref": cr,
                "openalex": oa,
            }

            ft_tasks = []
            ft_papers = []
            for paper in all_papers:
                client = client_map.get(paper.source)
                if client is not None:
                    ft_tasks.append(
                        _fetch_full_text_safe(client, paper)  # type: ignore[arg-type]
                    )
                    ft_papers.append(paper)

            ft_results = await asyncio.gather(*ft_tasks, return_exceptions=True)
            for paper, text in zip(ft_papers, ft_results):
                if isinstance(text, str) and text and not _is_binary(text):
                    paper.full_text = FullText(
                        format=FullTextFormat.XML
                        if text.lstrip().startswith("<")
                        else FullTextFormat.PLAIN,
                        content=text,
                    )

        # ── Phase 3: abstract fallback ────────────────────────────────────────
        # Papers without fetched full text but with a usable abstract are kept;
        # the extractor will work from the abstract and the Citation Investigator
        # can still resolve referenced papers.
        abstract_used = 0
        for paper in all_papers:
            if paper.full_text is None and paper.abstract and len(paper.abstract) > 100:
                paper.full_text = FullText(
                    format=FullTextFormat.PLAIN,
                    content=paper.abstract,
                    is_abstract_only=True,
                )
                abstract_used += 1
        if abstract_used:
            logger.info(
                "Abstract fallback applied to %d papers with no full text.",
                abstract_used,
            )

        return all_papers


async def _fetch_full_text_safe(client: object, paper: Paper) -> str | None:
    try:
        return await client.fetch_full_text(paper)  # type: ignore[attr-defined]
    except Exception as exc:  # noqa: BLE001
        logger.warning("Full-text fetch error for '%s': %s", paper.title[:60], exc)
        return None


def _is_binary(text: str) -> bool:
    """Return True if the string looks like raw binary (e.g. a PDF byte stream)."""
    if text.startswith("%PDF"):
        return True
    # More than 5% non-printable bytes → treat as binary
    non_printable = sum(1 for c in text[:2000] if ord(c) < 9 or (13 < ord(c) < 32))
    return non_printable > len(text[:2000]) * 0.05
