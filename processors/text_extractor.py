"""Step 4 – Text Extraction.

Convert raw full-text content stored by Step 3 into clean, normalised
plain text that downstream steps (filtering, protocol extraction) can
process reliably.

Supported input formats
-----------------------
* **PDF** – base-64 encoded bytes decoded and extracted with *pdfminer.six*
  (gracefully skipped when the library is not installed).
* **XML** – JATS / NLM XML stripped via :mod:`xml.etree.ElementTree` with a
  regex fallback for malformed documents.
* **HTML** – tag-stripped with the stdlib :class:`html.parser.HTMLParser`.
* **PLAIN** – returned unchanged.
"""
from __future__ import annotations

import base64
import html
import io
import logging
import re
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from typing import List, Optional

from models.paper import FullText, FullTextFormat, Paper

logger = logging.getLogger(__name__)

# Prefer PyMuPDF (fitz) for speed; fall back to pdfminer when absent.
try:
    import fitz  # type: ignore

    _PYMUPDF_AVAILABLE = True
except ImportError:
    _PYMUPDF_AVAILABLE = False
    logger.debug("PyMuPDF not installed – fast PDF extraction disabled.")

try:
    from pdfminer.high_level import extract_text as _pdf_extract_text  # type: ignore

    _PDFMINER_AVAILABLE = True
except ImportError:
    _PDFMINER_AVAILABLE = False
    logger.debug("pdfminer.six not installed – PDF text extraction disabled.")

try:
    from lxml import html as lxml_html  # type: ignore
    from lxml import etree as lxml_etree  # type: ignore

    _LXML_AVAILABLE = True
except ImportError:
    _LXML_AVAILABLE = False
    logger.debug("lxml not installed – robust HTML recovery disabled.")

# Collapse runs of whitespace / newlines
_WHITESPACE_RE = re.compile(r"\s{2,}")


class TextExtractor:
    """Step 4: convert raw full-text payloads into normalised plain text."""

    def extract_all(self, papers: List[Paper]) -> List[Paper]:
        """
        Iterate over *papers*, extract clean text from each
        ``paper.full_text``.

        Returns only papers for which full text was successfully extracted
        (papers with no raw content or failed extraction are dropped).
        """
        extracted = converted = no_text = 0

        for paper in papers:
            if paper.full_text is None:
                # No raw content available.
                no_text += 1
                continue

            if paper.full_text.format == FullTextFormat.PLAIN:
                # Already plain text – normalise whitespace only
                paper.full_text.content = _normalise(paper.full_text.content)
                extracted += 1
                continue

            clean = self._to_plain(paper.full_text)
            if clean:
                paper.full_text = FullText(
                    # Preserve original format for provenance, but update content and abstract-only flag
                    format=paper.full_text.format,
                    content=clean,
                    is_abstract_only=paper.full_text.is_abstract_only,
                )
                converted += 1
            else:
                # Extraction failed; drop paper from output.
                paper.full_text = None
                no_text += 1

        with_text = [p for p in papers if p.full_text is not None]
        logger.info(
            "Step 4 – Text extraction: %d already plain | %d converted | %d no text (dropped) → %d kept.",
            extracted,
            converted,
            no_text,
            len(with_text),
        )
        return with_text

    # ── Format dispatchers ────────────────────────────────────────────────────

    def _to_plain(self, ft: FullText) -> Optional[str]:
        """Dispatch to the correct extractor based on *ft.format*."""
        if ft.format == FullTextFormat.PDF:
            return self._from_pdf(ft.content)
        if ft.format == FullTextFormat.XML:
            return self._from_xml(ft.content)
        if ft.format == FullTextFormat.HTML:
            return self._from_html(ft.content)
        # Unknown format – return as-is after normalisation
        return _normalise(ft.content) or None

    # ── PDF ───────────────────────────────────────────────────────────────────

    def _from_pdf(self, b64_content: str) -> Optional[str]:
        """Decode base-64 PDF bytes and extract text (PyMuPDF → pdfminer fallback)."""
        if _PYMUPDF_AVAILABLE:
            text = self._from_pdf_pymupdf(b64_content)
            if text:
                return text
        if _PDFMINER_AVAILABLE:
            return self._from_pdf_pdfminer(b64_content)
        logger.debug("Skipping PDF extraction: no PDF backend available.")
        return None

    def _from_pdf_pymupdf(self, b64_content: str) -> Optional[str]:
        """Fast PDF text extraction using PyMuPDF."""
        try:
            pdf_bytes = base64.b64decode(b64_content)
            with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
                parts = [page.get_text("text") for page in doc]
            return _normalise(" ".join(parts)) or None
        except Exception as exc:  # noqa: BLE001
            logger.warning("PDF text extraction via PyMuPDF failed: %s", exc)
            return None

    def _from_pdf_pdfminer(self, b64_content: str) -> Optional[str]:
        """PDF text extraction using pdfminer.six (slower fallback)."""
        try:
            pdf_bytes = base64.b64decode(b64_content)
            text = _pdf_extract_text(io.BytesIO(pdf_bytes))
            return _normalise(text) or None
        except Exception as exc:  # noqa: BLE001
            logger.warning("PDF text extraction via pdfminer failed: %s", exc)
            return None

    # ── XML ───────────────────────────────────────────────────────────────────

    def _from_xml(self, content: str) -> Optional[str]:
        """Extract all text nodes from an XML document (JATS / NLM format)."""
        try:
            root = ET.fromstring(content)
            parts = [text for text in root.itertext() if text.strip()]
            return _normalise(" ".join(parts)) or None
        except ET.ParseError:
            # Malformed XML – fall back to regex-based tag stripping
            text = re.sub(r"<[^>]+>", " ", content)
            return _normalise(text) or None

    # ── HTML ──────────────────────────────────────────────────────────────────

    def _from_html(self, content: str) -> Optional[str]:
        """Strip HTML tags and decode entities; tolerate malformed HTML."""
        # 1) Prefer lxml with recover mode for broken HTML payloads.
        if _LXML_AVAILABLE:
            try:
                parser = lxml_html.HTMLParser(encoding="utf-8", recover=True)
                root = lxml_html.fromstring(content, parser=parser)
                text = root.text_content()
                clean = _normalise(text)
                if clean:
                    return clean
            except (lxml_etree.ParserError, ValueError) as exc:
                logger.debug("lxml HTML recovery failed: %s", exc)

        # 2) Fallback to stdlib HTMLParser.
        try:
            extractor = _HTMLTextExtractor()
            extractor.feed(content)
            extractor.close()
            clean = _normalise(extractor.get_text())
            if clean:
                return clean
        except Exception as exc:  # noqa: BLE001
            logger.debug("stdlib HTML parsing failed: %s", exc)

        # 3) Last-resort regex cleanup for severely malformed payloads.
        text = re.sub(r"<[^>]+>", " ", content)
        return _normalise(html.unescape(text)) or None


# ── Helpers ───────────────────────────────────────────────────────────────────

def _normalise(text: str) -> str:
    """Collapse redundant whitespace and strip leading/trailing space."""
    return _WHITESPACE_RE.sub(" ", text).strip()


class _HTMLTextExtractor(HTMLParser):
    """Minimal HTML parser that collects visible text nodes."""

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


# ── Stand-alone entry point ───────────────────────────────────────────────────

if __name__ == "__main__":
    import logging  # noqa: F811

    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s [%(levelname)s] %(name)s – %(message)s",
        datefmt="%H:%M:%S",
    )

    from utils.intermediate_io import STEP4_FILE, STEP5_FILE, load_model_list, save_json
    from models.paper import Paper  # noqa: F811

    _papers = load_model_list(STEP4_FILE, Paper)
    _before = len(_papers)
    _extracted = TextExtractor().extract_all(_papers)
    save_json(_extracted, STEP5_FILE)
    print(f"{len(_extracted)} / {_before} papers have clean plain text.")
    print(f"Saved → intermediate_outputs/{STEP5_FILE}")
