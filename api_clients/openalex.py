"""OpenAlex API client.

Docs: https://docs.openalex.org/
"""
from __future__ import annotations

import logging
import re
from html.parser import HTMLParser
from typing import List, Optional

import base64

from models.paper import FullText, FullTextFormat, Paper
from .base import BaseAPIClient, clean_title

logger = logging.getLogger(__name__)

_WORKS_URL = "https://api.openalex.org/works"
_SINGLE_WORK_URL = "https://api.openalex.org/works/doi:{doi}"
_SELECT = "id,doi,title,authorships,abstract_inverted_index,publication_year,open_access,primary_location"
_FULLTEXT_SELECT = "open_access,best_oa_location,primary_location,locations"
_MIN_TEXT_CHARS = 4000
_LANDING_MARKERS = (
    "redirecting",
    "auto article locator",
    "document.getelementbyid",
    "window.location",
    "javascript",
    "sign in",
    "purchase",
    "subscribe",
    "buy article",
    "access through your institution",
    "name=\"access\" content=\"no\"",
)


class OpenAlexClient(BaseAPIClient):
    """Wrapper around the OpenAlex REST API."""

    RATE_CALLS = 10
    RATE_PERIOD = 1.0

    def _headers(self) -> dict[str, str]:
        return {"User-Agent": "Pipetly/1.0 (mailto:contact@pipetly.bot)"}

    async def search(self, query: str, max_results: int = 10) -> List[Paper]:
        params = {
            "search": query,
            "per-page": min(max_results, 50),
            "select": _SELECT,
        }
        try:
            resp = await self._get(_WORKS_URL, params=params, headers=self._headers())
            data = resp.json()
        except Exception as exc:  # noqa: BLE001
            logger.error("OpenAlex search failed: %s", exc)
            return []

        papers: list[Paper] = []
        for item in data.get("results", []):
            doi = (item.get("doi") or "").replace("https://doi.org/", "") or None
            title = clean_title(item.get("title", ""))
            authors = [
                a.get("author", {}).get("display_name", "")
                for a in item.get("authorships", [])
            ]
            abstract = _rebuild_abstract(item.get("abstract_inverted_index"))
            candidates = _extract_candidate_urls(item)
            oa_url = candidates[0] if candidates else None
            papers.append(
                Paper(
                    doi=doi,
                    title=title,
                    authors=authors,
                    abstract=abstract,
                    year=item.get("publication_year"),
                    source="openalex",
                    url=oa_url,
                )
            )
        return papers

    async def fetch_full_text(self, paper: Paper) -> Optional[FullText]:
        """Find the OA URL via DOI lookup, then download the content.

        For papers from any source, performs a DOI-based lookup against
        OpenAlex to discover an open-access URL.  Falls back to the stored
        ``paper.url`` only for papers already sourced from OpenAlex.
        """
        oa_url: Optional[str] = None
        candidates: list[str] = []

        if paper.doi:
            try:
                resp = await self._get(
                    _SINGLE_WORK_URL.format(doi=paper.doi),
                    params={"select": _FULLTEXT_SELECT},
                    headers=self._headers(),
                )
                data = resp.json()
                candidates.extend(_extract_candidate_urls(data))
            except Exception as exc:  # noqa: BLE001
                logger.debug("OpenAlex DOI lookup failed for %s: %s", paper.doi, exc)

        # Only fall back to the stored URL when it actually came from OpenAlex
        if paper.source == "openalex" and paper.url:
            candidates.append(paper.url)

        # Keep order stable while removing duplicates.
        unique_candidates: list[str] = []
        for url in candidates:
            if url and url not in unique_candidates:
                unique_candidates.append(url)

        if not unique_candidates:
            return None

        for oa_url in unique_candidates:
            try:
                ft = await self._download_candidate(oa_url)
                if ft is not None:
                    return ft
            except Exception as exc:  # noqa: BLE001
                logger.debug("OpenAlex candidate failed for %s (%s): %s", paper.doi, oa_url, exc)

        return None

    async def _download_candidate(self, oa_url: str) -> Optional[FullText]:
        resp = await self._get(oa_url, headers=self._headers())
        raw_bytes = resp.content
        if not raw_bytes:
            return None

        content_type = (resp.headers.get("content-type") or "").lower()
        probe = raw_bytes[:1024].lstrip(b"\xef\xbb\xbf\r\n\t ")
        if "application/pdf" in content_type or probe.startswith(b"%PDF"):
            b64 = base64.b64encode(raw_bytes).decode("ascii")
            return FullText(format=FullTextFormat.PDF, content=b64)

        text = raw_bytes.decode("utf-8", errors="replace").strip()
        if not text:
            return None

        head = text[:3000].lower().lstrip()
        is_html = head.startswith("<") and ("<html" in head or "<!doctype" in head)

        # Some landing pages expose a direct PDF link in metadata.
        if is_html:
            meta_pdf_url = _extract_meta_pdf_url(text)
            if meta_pdf_url and meta_pdf_url != oa_url:
                try:
                    pdf_resp = await self._get(meta_pdf_url, headers=self._headers())
                    pdf_probe = pdf_resp.content[:1024].lstrip(b"\xef\xbb\xbf\r\n\t ")
                    if ("application/pdf" in (pdf_resp.headers.get("content-type") or "").lower()) or pdf_probe.startswith(b"%PDF"):
                        b64 = base64.b64encode(pdf_resp.content).decode("ascii")
                        return FullText(format=FullTextFormat.PDF, content=b64)
                except Exception as exc:  # noqa: BLE001
                    logger.debug("OpenAlex meta PDF candidate failed for %s: %s", meta_pdf_url, exc)

        if is_html and _looks_like_landing_or_preview(text):
            return None

        plain_len = len(_html_visible_text(text)) if is_html else len(_collapse_ws(text))
        if plain_len < _MIN_TEXT_CHARS:
            return None

        fmt = FullTextFormat.HTML if is_html else FullTextFormat.PLAIN
        return FullText(format=fmt, content=text)


def _rebuild_abstract(inverted_index: Optional[dict]) -> Optional[str]:
    """Reconstruct abstract text from OpenAlex inverted index."""
    if not inverted_index:
        return None
    words: dict[int, str] = {}
    for word, positions in inverted_index.items():
        for pos in positions:
            words[pos] = word
    if not words:
        return None
    return " ".join(words[i] for i in sorted(words))


def _extract_candidate_urls(record: dict) -> list[str]:
    """Return OA candidates with direct PDF links first."""
    out: list[str] = []

    def _push(url: Optional[str]) -> None:
        if url and url not in out:
            out.append(url)

    best = record.get("best_oa_location") or {}
    primary = record.get("primary_location") or {}
    open_access = record.get("open_access") or {}
    locations = record.get("locations") or []

    for loc in [best, primary, *locations]:
        if not isinstance(loc, dict):
            continue
        _push(loc.get("pdf_url"))
        _push((loc.get("source") or {}).get("hosted_fulltext_url"))

    _push(open_access.get("oa_url"))

    for loc in [best, primary, *locations]:
        if not isinstance(loc, dict):
            continue
        _push(loc.get("landing_page_url"))

    return out


def _looks_like_landing_or_preview(text: str) -> bool:
    body = text[:8000].lower()
    marker_hits = sum(1 for marker in _LANDING_MARKERS if marker in body)
    plain_len = len(_strip_tags_and_normalise(body))
    return marker_hits >= 2 or plain_len < _MIN_TEXT_CHARS


def _strip_tags_and_normalise(text: str) -> str:
    no_boilerplate = re.sub(r"(?is)<(script|style|noscript)[^>]*>.*?</\\1>", " ", text)
    no_boilerplate = re.sub(r"(?is)<head[^>]*>.*?</head>", " ", no_boilerplate)
    return _collapse_ws(re.sub(r"<[^>]+>", " ", no_boilerplate))


def _collapse_ws(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _extract_meta_pdf_url(html_text: str) -> Optional[str]:
    match = re.search(
        r"<meta[^>]+name=[\"']citation_pdf_url[\"'][^>]+content=[\"']([^\"']+)[\"']",
        html_text,
        flags=re.IGNORECASE,
    )
    return match.group(1).strip() if match else None


def _html_visible_text(html_text: str) -> str:
    parser = _HTMLVisibleExtractor()
    parser.feed(html_text)
    parser.close()
    return _collapse_ws(parser.get_text())


class _HTMLVisibleExtractor(HTMLParser):
    _SKIP_TAGS = frozenset({"script", "style", "head", "noscript"})

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._parts: list[str] = []
        self._skip_depth: int = 0

    def handle_starttag(self, tag: str, attrs: list) -> None:
        if tag.lower() in self._SKIP_TAGS:
            self._skip_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() in self._SKIP_TAGS and self._skip_depth > 0:
            self._skip_depth -= 1

    def handle_data(self, data: str) -> None:
        if self._skip_depth == 0:
            self._parts.append(data)

    def get_text(self) -> str:
        return " ".join(self._parts)
