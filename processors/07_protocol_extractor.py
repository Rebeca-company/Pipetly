"""Recursive protocol extraction processor.

Implements Step 7 as four explicit recursive sub-steps:
- Step 7.1: Identify protocol intervals (LLM)
- Step 7.2: Identify inherited references (LLM)
- Step 7.3: Resolve citation metadata from references section and fetch full text
- Step 7.4: Recurse into inherited protocol extraction until max depth
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import re
import time as _time
from typing import Any, Dict, Optional

import httpx

from config import get_settings
from utils.llm_client import BaseLLMProcessor
from api_clients import (
    CrossRefClient,
    ElsevierClient,
    EuropePMCClient,
    OpenAlexClient,
    PMCClient,
    ScopusClient,
    SemanticScholarClient,
    UnpaywallClient,
)
from models.paper import FullText, FullTextFormat, Paper
from models.protocol import (
    ExtractedProtocol,
    InheritedReference,
    InheritedReferencesOutput,
    ProtocolIntervalOutput,
    ReferenceMetadataOutput,
)
import importlib

TextExtractor = importlib.import_module("processors.05_text_extractor").TextExtractor

logger = logging.getLogger(__name__)
_s = get_settings()

_REFERENCES_WORD = re.compile(r"\b(referenc|bibliogr)", re.IGNORECASE)
_DOI_PATTERN = re.compile(r"10\.\d{4,9}/[^\s\]\[\)\(\"'<>]+", re.IGNORECASE)
_DOI_PREFIX_PATTERN = re.compile(
    r"^(?:https?://(?:dx\.)?doi\.org/|doi:)", flags=re.IGNORECASE
)
_YEAR_PATTERN = re.compile(r"(?:19|20)\d{2}")


_STEP_7_1_SYSTEM = """You are a specialized biomedical protocol extraction engine. Your goal is to identify and extract laboratory procedures and the external sources necessary to replicate them.

## Your task
Extract the experimental procedure from the provided scientific paper that matches the User Intent.
Evaluate the relevance of the extracted protocol to the user intent and assign a relevance score from 0 to 100.

## EXTRACTION RULES
1. **Intent filtering:** If the paper does not contain any protocol that matches the user intent, return an empty `protocol_text` and a `relevance_score` of 0.

2. **Verbatim sentence-level extraction:** 
    - Build `protocol_text` using the paper’s original text (no summarization).
    - Bias strongly toward including too much procedural detail rather than too little.
    - Preserve all technical values: catalogue numbers, vendors, buffer compositions, speeds, volumes, temperatures, pH, wavelengths, software versions, and exclusion rules.
    - If the protocol is split across sections (Methods/Results/Figure legends/Supplementary), concatenate the paragraphs preserving their original wording.
    - Keep the original order of sentences and sections.
    - Target specific scope: If the user intent targets a specific downstream stage or sub-procedure, extract only the text relevant to that requested sub-stage rather than the entire pipeline.

3. **Scoring:** Assign `relevance_score` (0-100) based on how well the extracted protocol allows for physical replication of the user intent. Consider the following criteria:
    - **Intent Alignment / Relevance (Weight: 50%):** Does the extracted protocol directly address the user's specific technique, biological target, or research intent? A strong mismatch here should cap the overall score low.
    - **Operational Completeness (Weight: 25%):** Are all steps, reagents, equipment, and measurable parameters expected for this technique present in the extracted text? (Note: Missing details can be supplemented if references are extracted).
    - **Parameter Plausibility (Weight: 15%):** Are the numerical values and conditions present internally consistent and physicochemically plausible?
    - **Executability (Weight: 10%):** Given the extracted content, are the instructions explicit and unambiguous enough that a researcher could act on them?
"""

_STEP_7_1_SCHEMA: dict[str, Any] = {
    "name": "step_7_1_protocol_interval",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "protocol_text": {"type": "string"},
            "relevance_score": {"type": "number"},
        },
        "required": ["protocol_text", "relevance_score"],
        "additionalProperties": False,
    },
}

_STEP_7_2_SYSTEM = """You identify inherited protocol references (Procedural Dependency) in experimental text.

## Your task
Given extracted protocol text, find references where methodological details are delegated to external papers/methods.

## Rules:
- If the protocol offloads the "how-to" of a key step to another paper, include an `inherited_references`.
- Include in inherited_references **ONLY** if the cited source has to be consulted to physically replicate a laboratory action (e.g., "prepared as described in...", "assayed following...").
- Prefer an empty list rather than including inherited references unnecessary to protocol execution.

## Exclusion rules (do NOT include as inherited references):
Do NOT include inherited references in the following cases:
- NO Clinical/Biological Context: Exclude citations used to justify the study, explain disease mechanisms, or provide reference ranges (e.g., "Normal LDH levels are 10-20% [5]").
- NO Background Findings: Exclude citations of previous results or applications (e.g., "Smith et al. used this to detect pregnancy [8]").
- NO Software/Statistics/Databases: Exclude ImageJ, GraphPad, ANOVA, or database citations (e.g., UniProt, STRING).
- NO General Equipment/Materials: Exclude citations that only identify a commercial kit or reagent unless the text says the *method* was followed from that specific paper.

## For each inherited reference output:
- context_phrase: the exact anchor text (e.g., "RNA preparation was performed as described in Johnson et al. 2022 [6]", "following the procedure of cell culture [3]") from protocol text that signals inheritance.
- search_intent: short actionable intent that should be used to search the inherited method (e.g., "RNA preparation method", "Cell culture procedure").
- reference_text: cited reference string as it appears (e.g., "Johnson et al. 2022 [6]", "[3]").

## Example
Input Text:
"Samples were collected from patients with chronic inflammation [1]. RNA extraction was performed using the phenol-chloroform method as described by Chomczynski and Sacchi [2]. Data analysis was conducted using GraphPad Prism 9.0."
Output:
{
  "inherited_references": [
    {
      "context_phrase": "RNA extraction was performed using the phenol-chloroform method as described by Chomczynski and Sacchi [2]",
      "search_intent": "phenol-chloroform RNA extraction method",
      "reference_text": "Chomczynski and Sacchi [2]"
    }
  ]
}
Note: Reference [1] was excluded because it provides biological context (patient status), and GraphPad was excluded per the software rule.
"""

_STEP_7_2_SCHEMA: dict[str, Any] = {
    "name": "step_7_2_inherited_references",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "inherited_references": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "context_phrase": {"type": "string"},
                        "search_intent": {"type": ["string", "null"]},
                        "reference_text": {"type": ["string", "null"]},
                    },
                    "required": ["context_phrase", "search_intent", "reference_text"],
                    "additionalProperties": False,
                },
            }
        },
        "required": ["inherited_references"],
        "additionalProperties": False,
    },
}

_STEP_7_3_SYSTEM = _STEP_7_3_SYSTEM = """You are a bibliographic metadata resolver.

## Your Task
Given a target reference and a references section text (the bibliography section), extract the specific metadata for that reference.

## Rules:
1. **Identify the Match**: Locate the full entry in the reference section that corresponds to the provided target reference (e.g., "[2]" or "Chomczynski et al.").
2. **DOI Extraction**: If a DOI is present, extract it. 
3. **Title Extraction**: If the DOI is missing, capture the full title of the paper. 
4. **Target Year**: If the DOI is missing, extract the 4-digit publication year.
5. **No reference**: If the target reference is not found in the references section, return null for all fields. Do not use your internal knowledge to find DOIs. Use ONLY the provided text.
"""

_STEP_7_3_SCHEMA: dict[str, Any] = {
    "name": "step_7_3_reference_metadata",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "target_doi": {"type": ["string", "null"]},
            "target_title": {"type": ["string", "null"]},
            "target_year": {"type": ["integer", "null"]},
        },
        "required": ["target_doi", "target_title", "target_year"],
        "additionalProperties": False,
    },
}


class ProtocolExtractor(BaseLLMProcessor):
    """Recursive Step 7 processor (7.1-7.4) with token accounting."""

    FT_CLIENT_ORDER = [
        ElsevierClient,
        EuropePMCClient,
        PMCClient,
        SemanticScholarClient,
        UnpaywallClient,
        OpenAlexClient,
    ]

    SEARCH_CLIENT_ORDER = [
        EuropePMCClient,
        SemanticScholarClient,
        ElsevierClient,
        CrossRefClient,
        OpenAlexClient,
        ScopusClient,
    ]

    def __init__(
        self,
        max_depth: Optional[int] = None,
        max_concurrent_protocols: int = 8,
        max_concurrent_fetches: int = 5,
        max_concurrent_llm: int = _s.llm_max_concurrent,
    ) -> None:
        super().__init__("7")
        self._max_depth = (
            _s.max_citation_depth if _s.max_citation_depth is not None else max_depth
        )
        if self._max_depth is None:
            self._max_depth = 1

        self._protocol_semaphore = asyncio.Semaphore(max_concurrent_protocols)
        self._fetch_semaphore = asyncio.Semaphore(max_concurrent_fetches)
        self._llm_semaphore = asyncio.Semaphore(max_concurrent_llm)

        self._text_extractor = TextExtractor()
        self._http_client: Optional[httpx.AsyncClient] = None
        self._ft_clients: list[Any] = []
        self._search_clients: list[Any] = []

        # Full-text cache for inherited retrievals: key -> (plain_text, source_label).
        self._plain_cache: dict[str, tuple[Optional[str], Optional[str]]] = {}
        self._seed_plain_by_doi: dict[str, str] = {}
        self._seed_plain_by_title: dict[str, str] = {}

        # Cycle guard: (paper key, normalized intent)
        self._visited_protocol_nodes: set[tuple[str, str]] = set()

        # Aggregated token accounting
        self._llm_usage_by_step: dict[str, dict[str, int]] = {}

    async def extract_all(
        self,
        papers: list[Paper],
        user_intent: str,
    ) -> list[ExtractedProtocol]:
        """Run recursive Step 7 extraction for all input papers."""
        protocols: list[ExtractedProtocol] = []
        self._seed_cache_with_input_papers(papers)
        self._visited_protocol_nodes.clear()
        self._llm_token_events.clear()
        self._llm_usage_by_step.clear()
        self._llm_call_count = 0

        self._http_client = httpx.AsyncClient(
            timeout=_s.http_timeout * 2,
            limits=httpx.Limits(max_keepalive_connections=20, max_connections=50),
        )

        try:
            async with contextlib.AsyncExitStack() as stack:
                self._ft_clients = [
                    await stack.enter_async_context(cls())
                    for cls in self.FT_CLIENT_ORDER
                ]
                self._search_clients = [
                    await stack.enter_async_context(cls())
                    for cls in self.SEARCH_CLIENT_ORDER
                ]

                tasks = [
                    self._extract_with_semaphore(paper, user_intent, depth=0)
                    for paper in papers
                ]
                results = await asyncio.gather(*tasks, return_exceptions=True)
        finally:
            if self._http_client is not None:
                await self._http_client.aclose()
                self._http_client = None

        protocols: list[ExtractedProtocol] = []
        for paper, result in zip(papers, results):
            if isinstance(result, Exception):
                logger.warning(
                    "Step 7 failed for paper '%s': %s",
                    paper.title[:100],
                    result,
                )
                continue
            if result is not None:
                protocols.append(result)

        self._log_llm_usage_summary()
        logger.info(
            "Recursive protocol extraction: Generated %d protocols from %d papers.",
            len(protocols),
            len(papers),
        )
        return protocols

    def get_llm_token_events(self) -> list[dict[str, Any]]:
        """Return per-call LLM token records for monitoring."""
        return list(self._llm_token_events)

    async def _extract_with_semaphore(
        self,
        paper: Paper,
        user_intent: str,
        depth: int,
    ) -> Optional[ExtractedProtocol]:
        async with self._protocol_semaphore:
            return await self._extract_protocol_recursive(paper, user_intent, depth)

    async def _extract_protocol_recursive(
        self,
        paper: Paper,
        user_intent: str,
        depth: int,
    ) -> Optional[ExtractedProtocol]:
        if depth > self._max_depth:
            return None

        paper_key = _paper_key(paper)
        intent_key = _normalize_title(user_intent)
        visit_key = (paper_key, intent_key)
        if visit_key in self._visited_protocol_nodes:
            logger.debug(
                "Step 7.%d skip - cycle detected for paper '%s' and intent '%s'.",
                depth,
                paper.title[:100],
                user_intent[:100],
            )
            return None
        self._visited_protocol_nodes.add(visit_key)

        plain_text = _extract_plain_text_from_paper(paper)
        if not plain_text:
            return None

        # Step 7.1
        step_7_1_payload = await self._step_7_1_identify_protocol_intervals(
            user_intent=user_intent,
            paper_text=plain_text,
            source_paper=paper,
            depth=depth,
        )
        if step_7_1_payload is None:
            return None

        protocol_text = step_7_1_payload.protocol_text.strip()
        score = max(0.0, min(100.0, step_7_1_payload.relevance_score))
        if score == 0.0 and not protocol_text:
            return None

        # Only continue with Steps 7.2-7.4 when Step 7.1 is strongly relevant.
        if score <= 40.0:
            logger.info(
                "Step 7.1 (depth=%d) - score %.2f <= 40; skipping Steps 7.2-7.4 for '%s'.",
                depth,
                score,
                paper.title[:100],
            )
            return None

        # Increment and validate recursive depth before extracting inherited refs.
        next_depth = depth + 1
        if next_depth > self._max_depth:
            logger.info(
                "Step 7.1 (depth=%d) - max depth %d reached; skipping Step 7.2 inherited-reference extraction for '%s'.",
                depth,
                self._max_depth,
                paper.title[:100],
            )
            return ExtractedProtocol(
                source_doi=paper.doi,
                source_title=paper.title,
                protocol_text=protocol_text,
                relevance_score=score,
                inherited_references=[],
                recursion_depth=depth,
                nested_protocols=[],
            )

        # Step 7.2
        inherited_refs = await self._step_7_2_identify_inherited_references(
            protocol_text=protocol_text,
            source_paper=paper,
            depth=depth,
        )

        references_section = _extract_references_section(plain_text)
        nested_protocols: list[ExtractedProtocol] = []

        for inherited_ref in inherited_refs:
            # Step 7.3
            (
                child_paper,
                child_plain_text,
                full_text_found_by,
            ) = await self._step_7_3_metadata_and_fulltext_retrieval(
                inherited_reference=inherited_ref,
                references_section=references_section,
                source_paper=paper,
                depth=depth,
            )
            if child_paper is None or not child_plain_text:
                continue

            if full_text_found_by:
                inherited_ref.full_text_found_by = full_text_found_by

            # Step 7.4
            nested = await self._step_7_4_recursive_protocol_fetch(
                inherited_reference=inherited_ref,
                child_paper=child_paper,
                child_plain_text=child_plain_text,
                depth=depth,
            )
            if nested is None:
                continue

            nested_protocols.append(nested)
            inherited_ref.resolved_fragment = nested.protocol_text or None
            inherited_ref.resolution_depth = next_depth

        return ExtractedProtocol(
            source_doi=paper.doi,
            source_title=paper.title,
            protocol_text=protocol_text,
            relevance_score=score,
            inherited_references=inherited_refs,
            recursion_depth=depth,
            nested_protocols=nested_protocols,
        )

    async def _step_7_1_identify_protocol_intervals(
        self,
        user_intent: str,
        paper_text: str,
        source_paper: Paper,
        depth: int,
    ) -> Optional[ProtocolIntervalOutput]:
        logger.info(
            "Step 7.1 (depth=%d) - protocol interval extraction for '%s'.",
            depth,
            source_paper.title[:100],
        )
        prompt = f"User intent:\n{user_intent}\n\nPaper full text:\n{paper_text}"
        raw = await self._call_llm_json(
            step_key="7.1",
            model=_s.llm_model_general,
            system_prompt=_STEP_7_1_SYSTEM,
            user_prompt=prompt,
            schema=_STEP_7_1_SCHEMA,
        )
        if raw is None:
            return None
        try:
            return ProtocolIntervalOutput.model_validate(raw)
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "Step 7.1 (depth=%d) - ProtocolIntervalOutput validation failed for '%s': %s",
                depth,
                source_paper.title[:100],
                exc,
            )
            return None

    async def _step_7_2_identify_inherited_references(
        self,
        protocol_text: str,
        source_paper: Paper,
        depth: int,
    ) -> list[InheritedReference]:
        if not protocol_text.strip():
            return []

        logger.info(
            "Step 7.2 (depth=%d) - inherited reference extraction for '%s'.",
            depth,
            source_paper.title[:100],
        )
        prompt = f"Protocol text:\n{protocol_text}"
        raw = await self._call_llm_json(
            step_key="7.2",
            model=_s.llm_model_general,
            system_prompt=_STEP_7_2_SYSTEM,
            user_prompt=prompt,
            schema=_STEP_7_2_SCHEMA,
        )
        if raw is None:
            return []

        try:
            parsed = InheritedReferencesOutput.model_validate(raw)
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "Step 7.2 (depth=%d) - InheritedReferencesOutput validation failed for '%s': %s",
                depth,
                source_paper.title[:100],
                exc,
            )
            return []

        refs: list[InheritedReference] = []
        seen: set[tuple[str, str]] = set()

        for item in parsed.inherited_references:
            context_phrase = (item.context_phrase or "").strip()
            search_intent = (item.search_intent or "").strip() or None
            reference_text = (item.reference_text or "").strip() or None

            if not context_phrase:
                continue

            dedup_key = (
                _normalize_title(context_phrase),
                _normalize_title(reference_text or ""),
            )
            if dedup_key in seen:
                continue
            seen.add(dedup_key)

            refs.append(
                InheritedReference(
                    context_phrase=context_phrase,
                    search_intent=search_intent,
                    reference_text=reference_text,
                )
            )

        logger.info(
            "Step 7.2 (depth=%d) - extracted %d inherited references for '%s'.",
            depth,
            len(refs),
            source_paper.title[:100],
        )
        return refs

    async def _step_7_3_metadata_and_fulltext_retrieval(
        self,
        inherited_reference: InheritedReference,
        references_section: str,
        source_paper: Paper,
        depth: int,
    ) -> tuple[Optional[Paper], Optional[str], Optional[str]]:
        reference_text = (
            inherited_reference.reference_text or ""
        ).strip() or inherited_reference.context_phrase.strip()
        if not reference_text:
            return None, None, None

        logger.info(
            "Step 7.3 (depth=%d) - metadata/full-text retrieval for reference '%s' in '%s'.",
            depth,
            reference_text[:100],
            source_paper.title[:100],
        )

        target_doi: Optional[str] = None
        target_title: Optional[str] = None
        target_year: Optional[int] = None

        prompt = (
            f"Target inherited reference:\n{reference_text}\n\n"
            "References section text:\n"
            f"{references_section}"
        )
        metadata = await self._call_llm_json(
            step_key="7.3",
            model=_s.llm_model_general,
            system_prompt=_STEP_7_3_SYSTEM,
            user_prompt=prompt,
            schema=_STEP_7_3_SCHEMA,
            extra_log_context=f"depth={depth}",
        )
        if metadata is not None:
            try:
                ref_meta = ReferenceMetadataOutput.model_validate(metadata)
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "Step 7.3 (depth=%d) - ReferenceMetadataOutput validation failed for '%s': %s",
                    depth,
                    reference_text[:100],
                    exc,
                )
                ref_meta = ReferenceMetadataOutput()

            if ref_meta.target_doi:
                # Keep DOI normalization consistent with full-text retrieval.
                target_doi = _normalize_doi(ref_meta.target_doi.strip()) or None
            target_title = (ref_meta.target_title or "").strip() or None
            target_year = ref_meta.target_year

            if target_doi:
                inherited_reference.target_doi = target_doi
            if target_title:
                inherited_reference.target_title = target_title
            if target_year is not None:
                inherited_reference.target_year = target_year

        if not (target_doi or target_title):
            logger.info(
                "Step 7.3 (depth=%d) - metadata unresolved for reference '%s'.",
                depth,
                reference_text[:100],
            )
            return None, None, None

        candidate_paper: Optional[Paper]
        if target_doi:
            candidate_paper = Paper(
                doi=target_doi,
                title=target_title or reference_text,
                authors=[],
                abstract=None,
                year=target_year,
                source="inherited_protocol_resolution",
                url=None,
            )
        else:
            candidate_paper = await self._search_by_title(
                target_title or reference_text, target_year
            )
            if candidate_paper is None:
                candidate_paper = Paper(
                    doi=None,
                    title=target_title or reference_text,
                    authors=[],
                    abstract=None,
                    year=target_year,
                    source="inherited_protocol_resolution",
                    url=None,
                )

        if candidate_paper.doi:
            candidate_paper.doi = _normalize_doi(candidate_paper.doi) or None

        if candidate_paper.doi and not inherited_reference.target_doi:
            inherited_reference.target_doi = candidate_paper.doi
        if candidate_paper.title and not inherited_reference.target_title:
            inherited_reference.target_title = candidate_paper.title
        if candidate_paper.year is not None and inherited_reference.target_year is None:
            inherited_reference.target_year = candidate_paper.year

        child_plain_text, full_text_found_by = await self._fetch_plain_text_cached(
            candidate_paper
        )
        if not child_plain_text:
            logger.info(
                "Step 7.3 (depth=%d) - full text not available for '%s'.",
                depth,
                candidate_paper.title[:100],
            )
            return candidate_paper, None, None

        return candidate_paper, child_plain_text, full_text_found_by

    async def _step_7_4_recursive_protocol_fetch(
        self,
        inherited_reference: InheritedReference,
        child_paper: Paper,
        child_plain_text: str,
        depth: int,
    ) -> Optional[ExtractedProtocol]:
        next_depth = depth + 1
        if next_depth > self._max_depth:
            return None

        nested_intent = (
            inherited_reference.search_intent or ""
        ).strip() or inherited_reference.context_phrase.strip()
        if not nested_intent:
            return None

        logger.info(
            "Step 7.4 (depth=%d) - recursive extraction for '%s' with intent '%s'.",
            next_depth,
            child_paper.title[:100],
            nested_intent[:100],
        )

        child = child_paper.model_copy(deep=True)
        child.full_text = FullText(
            format=FullTextFormat.PLAIN,
            content=child_plain_text,
        )

        return await self._extract_protocol_recursive(child, nested_intent, next_depth)

    async def _search_by_title(
        self, title: str, target_year: Optional[int]
    ) -> Optional[Paper]:
        title = title.strip()
        if not title:
            return None

        clients = [
            client for client in self._search_clients if hasattr(client, "search")
        ]
        if not clients:
            return None

        tasks = [
            client.search(title, max_results=3)  # type: ignore[attr-defined]
            for client in clients
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        candidates: list[Paper] = []
        for item in results:
            if isinstance(item, Exception):
                continue
            candidates.extend(item)

        deduped = _deduplicate_papers(candidates)
        if not deduped:
            return None
        return _find_best_title_match(title, deduped, target_year)

    async def _fetch_plain_text_cached(
        self, paper: Paper
    ) -> tuple[Optional[str], Optional[str]]:
        cache_key = _paper_key(paper)

        if paper.doi:
            seed = self._seed_plain_by_doi.get(_normalize_doi(paper.doi))
            if seed and self._passes_full_text_filter(seed):
                return seed, "step6_seed_doi"

        title_key = _normalize_title(paper.title)
        if title_key:
            seed = self._seed_plain_by_title.get(title_key)
            if seed and self._passes_full_text_filter(seed):
                return seed, "step6_seed_title"

        if cache_key in self._plain_cache:
            cached_text, cached_source = self._plain_cache[cache_key]
            if cached_text and self._passes_full_text_filter(cached_text):
                return cached_text, cached_source
            return None, None

        async with self._fetch_semaphore:
            if cache_key in self._plain_cache:
                cached_text, cached_source = self._plain_cache[cache_key]
                if cached_text and self._passes_full_text_filter(cached_text):
                    return cached_text, cached_source
                return None, None

            fetched_text, fetched_source = await self._fetch_plain_text(paper)
            self._plain_cache[cache_key] = (fetched_text, fetched_source)
            return fetched_text, fetched_source

    async def _fetch_plain_text(
        self, paper: Paper
    ) -> tuple[Optional[str], Optional[str]]:
        # If paper already has full text, normalise it through TextExtractor first.
        if paper.full_text and paper.full_text.content.strip():
            plain = self._extract_and_validate_plain_text(
                paper=paper,
                full_text=paper.full_text,
                source_label="existing",
            )
            if plain:
                return plain, "existing"

        for client in self._ft_clients:
            try:
                ft = await client.fetch_full_text(paper)  # type: ignore[attr-defined]
                if not ft or not ft.content.strip():
                    continue

                converted_text = self._extract_and_validate_plain_text(
                    paper=paper,
                    full_text=ft,
                    source_label=type(client).__name__,
                )
                if converted_text:
                    return converted_text, type(client).__name__
            except Exception as exc:  # noqa: BLE001
                logger.debug(
                    "Inherited full-text fetch failed via %s for '%s': %s",
                    type(client).__name__,
                    paper.title[:100],
                    exc,
                )
                continue

        return None, None

    def _extract_and_validate_plain_text(
        self,
        *,
        paper: Paper,
        full_text: FullText,
        source_label: str,
    ) -> Optional[str]:
        work = paper.model_copy(deep=True)
        work.full_text = full_text
        converted = self._text_extractor.extract_all([work])
        if not converted:
            return None

        plain = _extract_plain_text_from_paper(converted[0])
        if not plain:
            return None

        if not self._passes_full_text_filter(plain):
            logger.debug(
                "Inherited full-text rejected by Step 6 length filter via %s for '%s' (%d chars).",
                source_label,
                paper.title[:100],
                len(plain),
            )
            return None

        return plain

    def _passes_full_text_filter(self, text: str) -> bool:
        # Mirror Step 6 FullTextFilter criteria.
        cleaned = text.strip()
        if not cleaned:
            return False

        text_len = len(cleaned)
        if text_len < _s.full_text_min_chars:
            return False
        if text_len > _s.full_text_max_chars:
            return False
        return True

    async def _call_llm_json(
        self,
        *,
        step_key: str,
        model: str,
        system_prompt: str,
        user_prompt: str,
        schema: dict[str, Any],
        extra_log_context: str = "",
    ) -> Optional[Dict[str, Any]]:
        if self._http_client is None:
            logger.error("LLM client is not initialized for step %s.", step_key)
            return None

        payload: dict[str, Any] = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.0,
            "response_format": {"type": "json_schema", "json_schema": schema},
        }

        async with self._llm_semaphore:
            try:
                _t0 = _time.monotonic()
                resp = await self._http_client.post(
                    f"{self._base}/chat/completions",
                    json=payload,
                    headers=self._headers,
                )
                _gen_ms = (_time.monotonic() - _t0) * 1000
                if resp.is_error:
                    logger.error(
                        "OpenRouter error on step %s %s: %s - %s",
                        step_key,
                        extra_log_context,
                        resp.status_code,
                        resp.text,
                    )
                    resp.raise_for_status()

                raw_payload = resp.json()
                self._record_llm_usage(raw_payload, step_key=step_key, generation_time_ms=_gen_ms)

                content = (
                    raw_payload.get("choices", [{}])[0]
                    .get("message", {})
                    .get("content", "{}")
                )

                if isinstance(content, list):
                    content = "".join(
                        part.get("text", "") if isinstance(part, dict) else str(part)
                        for part in content
                    )

                if not isinstance(content, str):
                    content = str(content)

                return json.loads(content)
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "LLM call failed on step %s %s: %s",
                    step_key,
                    extra_log_context,
                    exc,
                )
                return None

    def _log_llm_usage_summary(self) -> None:
        events = self.get_llm_token_events()
        if not events:
            logger.info("LLM usage summary - no calls recorded.")
            return

        by_step = {}
        for ev in events:
            sk = ev.get("step", "7")
            if sk not in by_step:
                by_step[sk] = {
                    "calls": 0,
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "total_tokens": 0,
                }
            by_step[sk]["calls"] += 1
            by_step[sk]["input_tokens"] += ev.get("input_tokens", 0)
            by_step[sk]["output_tokens"] += ev.get("output_tokens", 0)
            by_step[sk]["total_tokens"] += ev.get("total_tokens", 0)

        logger.info("LLM usage summary by step:")
        for step_key in sorted(by_step.keys()):
            item = by_step[step_key]
            logger.info(
                "  Step %s: calls=%d input_tokens=%d output_tokens=%d total_tokens=%d",
                step_key,
                item["calls"],
                item["input_tokens"],
                item["output_tokens"],
                item["total_tokens"],
            )

    def _seed_cache_with_input_papers(self, papers: list[Paper]) -> None:
        self._seed_plain_by_doi.clear()
        self._seed_plain_by_title.clear()

        for paper in papers:
            text = _extract_plain_text_from_paper(paper)
            if not text:
                continue

            if paper.doi:
                doi_key = _normalize_doi(paper.doi)
                if doi_key and doi_key not in self._seed_plain_by_doi:
                    self._seed_plain_by_doi[doi_key] = text

            title_key = _normalize_title(paper.title)
            if title_key and title_key not in self._seed_plain_by_title:
                self._seed_plain_by_title[title_key] = text


# ----------------------------
# Helper functions
# ----------------------------


def _extract_plain_text_from_paper(paper: Paper) -> Optional[str]:
    if not paper.full_text:
        return None
    text = (paper.full_text.content or "").strip()
    return text or None


def _extract_references_section(text: str) -> str:
    if not text:
        return ""
    # Full texts are often plain text without section-style headers.
    # Search only in the final half to avoid early narrative mentions.
    tail_start = len(text) // 2
    tail_text = text[tail_start:]
    match = _REFERENCES_WORD.search(tail_text)
    if match is None:
        return ""

    return text[tail_start + match.start() :]


def _normalize_doi(doi: str) -> str:
    normalized = _DOI_PREFIX_PATTERN.sub("", doi.strip()).lower()
    return normalized.rstrip("/.")


def _normalize_title(title: str) -> str:
    normalized = title.lower()
    normalized = re.sub(r"[^\w\s]", "", normalized)
    normalized = re.sub(r"\s+", "", normalized).strip()
    return normalized


def _get_title_tokens(title: str) -> set[str]:
    cleaned = re.sub(r"[^\w\s]", " ", title.lower())
    return {token for token in cleaned.split() if len(token) > 2}


def _paper_key(paper: Paper) -> str:
    if paper.doi:
        return f"doi:{_normalize_doi(paper.doi)}"
    return f"title:{_normalize_title(paper.title)}"


def _deduplicate_papers(papers: list[Paper]) -> list[Paper]:
    if not papers:
        return []

    doi_best: dict[str, Paper] = {}
    no_doi: list[Paper] = []

    for paper in papers:
        if paper.doi:
            key = _normalize_doi(paper.doi)
            if key not in doi_best or _paper_score(paper) > _paper_score(doi_best[key]):
                doi_best[key] = paper
        else:
            no_doi.append(paper)

    title_best: dict[str, Paper] = {}
    for paper in [*doi_best.values(), *no_doi]:
        key = _normalize_title(paper.title)
        if not key:
            continue
        if key not in title_best or _paper_score(paper) > _paper_score(title_best[key]):
            title_best[key] = paper

    return list(title_best.values())


def _paper_score(paper: Paper) -> int:
    score = 0
    if paper.doi:
        score += 3
    if paper.title:
        score += 2
    if paper.abstract:
        score += 2
    if paper.authors:
        score += min(len(paper.authors), 10)
    if paper.year:
        score += 1
    if paper.url:
        score += 1
    return score


def _find_best_title_match(
    target_title: str,
    candidates: list[Paper],
    target_year: Optional[int],
) -> Optional[Paper]:
    wanted = _normalize_title(target_title)
    if not wanted:
        return None

    if target_year is not None:
        with_year = [paper for paper in candidates if paper.year == target_year]
        if with_year:
            candidates = with_year

    exact = [paper for paper in candidates if _normalize_title(paper.title) == wanted]
    if exact:
        return _select_most_complete(exact)

    containment = [
        paper
        for paper in candidates
        if wanted in _normalize_title(paper.title)
        or _normalize_title(paper.title) in wanted
    ]
    if containment:
        return _select_most_complete(containment)

    wanted_tokens = _get_title_tokens(target_title)
    if not wanted_tokens:
        return None

    token_matches = []
    for paper in candidates:
        tokens = _get_title_tokens(paper.title)
        if not tokens:
            continue
        if wanted_tokens.issubset(tokens) or tokens.issubset(wanted_tokens):
            token_matches.append(paper)

    if token_matches:
        return _select_most_complete(token_matches)

    return None


def _select_most_complete(papers: list[Paper]) -> Optional[Paper]:
    if not papers:
        return None
    if len(papers) == 1:
        return papers[0]

    ranked = sorted(papers, key=_paper_score, reverse=True)
    if len(ranked) >= 2 and _paper_score(ranked[0]) == _paper_score(ranked[1]):
        return None
    return ranked[0]


if __name__ == "__main__":
    import asyncio
    from utils.logger import set_stage_logger, setup_logging

    setup_logging()
    set_stage_logger("step7_protocol_extraction")

    from config import get_settings
    from utils.telemetry import log_standalone_telemetry

    from models.query import ExpandedQuery
    from utils.intermediate_io import (
        STEP1_FILE,
        STEP6_FILE,
        STEP7_FILE,
        load_model,
        load_model_list,
        save_json,
    )

    async def _main() -> None:
        logger.info("[Step 7] START | Recursive Protocol Extraction")
        _s = get_settings()
        papers = load_model_list(STEP6_FILE, Paper)
        intent = load_model(STEP1_FILE, ExpandedQuery).intent

        extractor = ProtocolExtractor(max_depth=_s.max_citation_depth)
        protocols = await extractor.extract_all(papers, intent)

        save_json(protocols, STEP7_FILE)

        logger.info("Extracted %d recursive protocols.", len(protocols))
        logger.info(
            "[Step 7] DONE | input=%d output=%d | Output: intermediate_outputs/%s",
            len(papers),
            len(protocols),
            STEP7_FILE,
        )

        events = extractor.get_llm_token_events()
        await log_standalone_telemetry(events, _s.llm_model_general, "protocol_extractor")

    asyncio.run(_main())
