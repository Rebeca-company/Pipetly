# Pipetly 🧪

**Automated extraction of biomedical protocols from scientific literature.**

Pipetly accepts a plain-language research question and returns a ranked, structured Markdown report of the most relevant experimental protocols found across multiple academic databases.

---

## How it works

```
User prompt
    │
    ▼
┌─────────────────────────────┐
│  1. Query Expansion         │  Gemini rewrites the prompt into keyword queries
│     (processors/)           │  (concept strings)
└────────────┬────────────────┘
             │
             ▼
┌─────────────────────────────┐
│  2. Multi-Source Fetch      │  Concurrent async calls to:
│     (processors/            │   • Europe PMC   • Semantic Scholar
│      paper_searcher.py)     │   • Elsevier     • CrossRef
│                             │   • OpenAlex     • Scopus
└────────────┬────────────────┘
             │
             ▼
┌─────────────────────────────┐
│  3. Metadata Filter         │  Deduplicates by DOI/title and removes no-DOI papers
│     (processors/            │
│      metadata_filter.py)    │
└────────────┬────────────────┘
             │
             ▼
┌─────────────────────────────┐
│  4. Full-Text Retrieval     │  Tries multiple providers and keeps the first
│     (processors/            │  valid full-text payload (XML/PDF/HTML/plain)
│      full_text_retriever.py)│
└────────────┬────────────────┘
             │
             ▼
┌─────────────────────────────┐
│  5. Text Extraction         │  Converts raw payload to clean plain text
│     (processors/            │
│      text_extractor.py)     │
└────────────┬────────────────┘
             │
             ▼
┌─────────────────────────────┐
│  6. Full-Text Length Filter │  Keeps papers in configured char-range
│     (processors/            │  (default: 10,000 to 200,000 chars)
│      full_text_filter.py)   │
└────────────┬────────────────┘
             │
             ▼
┌─────────────────────────────┐
│  7. Recursive Protocol      │  7.1 protocol interval extraction (LLM)
│     Extraction              │  7.2 inherited-reference detection (LLM)
│     (processors/            │  7.3 reference metadata + inherited full-text retrieval
│      protocol_extractor.py) │      (normalised to plain text + Step 6 length gating)
│                             │  7.4 recursive extraction over inherited protocols
└────────────┬────────────────┘
             │
             ▼
┌─────────────────────────────┐
│  8. Protocol Scoring        │  Re-scores protocols using only recursion levels
│     (processors/            │  0 and 1 inside each protocol tree
│      protocol_scorer.py)    │
└────────────┬────────────────┘
             │
             ▼
┌─────────────────────────────┐
│  9. Final Formatting        │  Integrates resolved inherited fragments into source
│     & Output                │  protocol text with citations ([DOI:...] or [REF:...])
│     (processors/            │  and drafts final numbered steps (LLM)
│      protocol_formatter.py) │
└─────────────────────────────┘
```

---

## Project structure

```
Pipetly/
├── main.py                   ← CLI entry-point
├── config.py                 ← All settings (pydantic-settings, loaded from .env)
├── requirements.txt
│
├── models/                   ← Pydantic v2 data schemas
│   ├── query.py              → ExpandedQuery
│   ├── paper.py              → Paper, FullText
│   └── protocol.py           → ExtractedProtocol, InheritedReference, ScoredProtocol
│
├── api_clients/              ← Async httpx wrappers (one file per source)
│   ├── base.py               → Shared retry logic & token-bucket rate limiter
│   ├── europe_pmc.py
│   ├── semantic_scholar.py
│   ├── elsevier.py
│   ├── crossref.py
│   ├── openalex.py
│   ├── scopus.py
│   ├── pmc.py
│   └── unpaywall.py
│
├── processors/               ← Pipeline stages
│   ├── query_expander.py     → Stage 1
│   ├── paper_searcher.py     → Stage 2
│   ├── metadata_filter.py    → Stage 3
│   ├── full_text_retriever.py→ Stage 4
│   ├── text_extractor.py     → Stage 5
│   ├── full_text_filter.py   → Stage 6
│   ├── protocol_extractor.py → Stage 7 (recursive 7.1-7.4)
│   ├── protocol_scorer.py    → Stage 8
│   └── protocol_formatter.py → Stage 9
│
└── utils/
    ├── rate_limiter.py       → Async token-bucket rate limiter
    ├── intermediate_io.py    → Stage file IO helpers
    └── json_utils.py         → JSON extraction helpers
```

---

## Requirements

- Python 3.11+
- A [conda](https://docs.conda.io/) environment named `pipetly` (or any venv)
- An [OpenRouter](https://openrouter.ai/) API key (used to call Gemini models)

---

## Installation

```bash
# 1. Clone the repository
git clone https://github.com/your-org/pipetly.git
cd Pipetly

# 2. Create and activate the conda environment
conda create -n pipetly python=3.11 -y
conda activate pipetly

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure secrets
cp .env.example .env
#    → open .env and set at least OPENROUTER_API_KEY
```

---

## Configuration

All configuration lives in `.env` (never committed to git):

| Variable | Required | Description |
|---|---|---|
| `OPENROUTER_API_KEY` | ✅ | Your key from [openrouter.ai/keys](https://openrouter.ai/keys) |
| `ELSEVIER_API_KEY` | ⬜ | [Elsevier Dev Portal](https://dev.elsevier.com/) – enables ScienceDirect full-text |
| `SEMANTIC_SCHOLAR_API_KEY` | ⬜ | [S2 API](https://www.semanticscholar.org/product/api) – higher rate limits |
| `UNPAYWALL_EMAIL` | ⬜ | Contact e-mail used by Unpaywall API |
| `NCBI_API_KEY` | ⬜ | Optional NCBI key for higher throughput where applicable |

Optional pipeline tunables (add to `.env` to override defaults):

| Variable | Default | Description |
|---|---|---|
| `MAX_PAPERS_PER_SOURCE` | `3` | Results fetched per API per query |
| `MAX_CITATION_DEPTH` | `2` | Max recursive citation-investigator depth |
| `TOP_K_PROTOCOLS` | `5` | Number of protocols to include in the final report |
| `HTTP_TIMEOUT` | `30.0` | Per-request timeout in seconds |
| `HTTP_MAX_RETRIES` | `4` | Max retries on rate-limit / connection errors |
| `LLM_MAX_CONCURRENT` | `20` | Shared max concurrent LLM calls across pipeline components |

---

## Usage

```bash
# Activate environment first
conda activate pipetly

# Run with a research question
python main.py "protocol for CRISPR-Cas9 knockout in human HEK293 cells"

# Multi-word queries don't need quotes on most shells, but quotes are safer
python main.py "western blot protocol for detection of phosphorylated ERK1/2"
```

The report is written to `output/protocols_<timestamp>.md`.

### Example output structure

```markdown
# Pipetly — Extracted Biomedical Protocols

**Search intent:** Step-by-step CRISPR-Cas9 knockout protocol in HEK293 cells
**Generated:** 2026-02-25T14:32:01

---

## Rank 1 — CRISPR-Cas9 Genome Editing in Human Cell Lines
**Source:** Efficient genome editing in human cells using CRISPR-Cas9
**DOI:** [10.1016/j.cell.2013.12.010](https://doi.org/10.1016/j.cell.2013.12.010)
**Relevance score:** 94.0/100

### Protocol Steps

1. Design sgRNA targeting the gene of interest.
2. Assemble expression constructs and validate sequence.
3. Transfect cells and apply selection conditions.
4. Screen edited clones and confirm the target modification [DOI:10.1016/j.cell.2013.12.010].

### Inherited References

- **Context:** ... as described in prior work
    **Target DOI:** [10.xxxx/xxxxx](https://doi.org/10.xxxx/xxxxx)
```

---

## Intermediate outputs

- `intermediate_outputs/step1_expanded_query.json`
- `intermediate_outputs/step2_raw_papers.json`
- `intermediate_outputs/step3_doi_filtered_papers.json`
- `intermediate_outputs/step4_fulltext_raw_papers.json`
- `intermediate_outputs/step5_fulltext_clean_papers.json`
- `intermediate_outputs/step6_fulltext_filtered_papers.json`
- `intermediate_outputs/step7_protocols.json`
- `intermediate_outputs/step8_scored_protocols.json`
- `intermediate_outputs/test_llm_token_usage.json` (testing telemetry)

---

## Architecture notes

- **Decoupled layers** — `models/` ↦ `api_clients/` ↦ `processors/` ↦ `utils/`; no circular imports.
- **Async throughout** — `httpx.AsyncClient` + `asyncio.gather` for concurrent multi-source fan-out.
- **Rate limiting** — each API client has its own `RateLimiter` (token-bucket); 429 responses trigger exponential backoff.
- **Staged full-text normalization** — Step 4 fetches raw payloads, Step 5 converts to clean plain text, and Step 6 applies length-based quality gating.
- **Recursive protocol reasoning** — Step 7 resolves inherited protocol references recursively (up to configured depth).
- **Controlled scoring context** — Step 8 scores only recursion levels 0 and 1 within each protocol tree.
- **Evidence-preserving formatting** — Step 9 integrates resolved inherited fragments with explicit citations before LLM step drafting.
- **Token/cost observability** — pipeline emits LLM token telemetry for extractor, scorer, and formatter into `test_llm_token_usage.json`.
- **Graceful degradation** — missing API keys silently skip that source; network errors are logged and the pipeline continues.

---

## License

See [LICENSE](LICENSE).
