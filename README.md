# Pipetly — Biomedical Protocol Extractor

Pipetly is an automated AI-powered pipeline that extracts structured, step-by-step experimental protocols from biomedical scientific literature. Given a natural-language research question, it retrieves papers from multiple academic databases, fetches and processes their full texts, and uses LLMs to build a complete, reproducible protocol — including details that the primary paper delegates to cited references.

All LLM calls are routed through **[OpenRouter](https://openrouter.ai)**, so any model available there can be used with a single configuration change.

---

## How it works — 9-step pipeline

```
User prompt
    │
    ▼
[Step 1] Query Expansion        → structured search queries + intent
    │
    ▼
[Step 2] Paper & Metadata Search → raw records from 6 search APIs (concurrent)
    │
    ▼
[Step 3] Metadata Filter         → deduplicate · require a valid DOI
    │
    ▼
[Step 4] Full-Text Retrieval     → PDF / XML / HTML from 6 retrieval APIs
    │
    ▼
[Step 5] Text Extraction         → clean plain text (abstract fallback)
    │
    ▼
[Step 6] Post-Extraction Filter  → keep papers within accepted length bounds
    │
    ▼
[Step 7] Recursive Protocol Extraction → LLM extracts protocol + follows cited refs
    │
    ▼
[Step 8] Protocol Scoring        → LLM re-scores fragments; keeps score > 60
    │
    ▼
[Step 9] Final Formatting        → Markdown report · token & time telemetry
    │
    ▼
output/<timestamp>.md
```

**Step 7** is the most complex step. It recursively resolves inherited references up to a configurable depth (`max_depth=3`): when the primary paper delegates protocol details to another paper, the extractor fetches that referenced paper and integrates its content into the final protocol.

After every step, the intermediate output is written as JSON to `intermediate_outputs/` so individual steps can be inspected or re-run independently.

---

## Repository Structure

```
Pipetly/
├── main.py                      # Entry point — runs the full pipeline
├── config.py                    # Settings (pydantic-settings, .env-based)
├── requirements.txt             # Python dependencies
├── .env.example                 # Template for environment variables
│
├── processors/                  # One module per pipeline step
│   ├── 01_query_expander.py
│   ├── 02_paper_searcher.py
│   ├── 03_metadata_filter.py
│   ├── 04_full_text_retriever.py
│   ├── 05_text_extractor.py
│   ├── 06_full_text_filter.py
│   ├── 07_protocol_extractor.py   # Recursive extraction + reference resolution
│   ├── 08_protocol_scorer.py
│   └── 09_protocol_formatter.py
│
├── api_clients/                 # API connectors (search + full-text retrieval)
│   ├── base.py
│   ├── crossref.py
│   ├── elsevier.py              # Requires ELSEVIER_API_KEY + ELSEVIER_INST_TOKEN
│   ├── europe_pmc.py
│   ├── openalex.py
│   ├── pmc.py
│   ├── scopus.py                # Requires ELSEVIER_API_KEY + ELSEVIER_INST_TOKEN
│   ├── semantic_scholar.py      # Higher rate limit with SEMANTIC_SCHOLAR_API_KEY
│   └── unpaywall.py             # Requires UNPAYWALL_EMAIL
│
├── models/                      # Pydantic data schemas
│   ├── paper.py                 # Paper, FullText, SearchResult, SearchTelemetry
│   ├── protocol.py              # ExtractedProtocol, ScoredProtocol, InheritedReference
│   └── query.py                 # ExpandedQuery
│
├── utils/
│   ├── intermediate_io.py       # JSON save/load helpers + step filename constants
│   ├── llm_client.py            # BaseLLMProcessor (shared OpenRouter client)
│   ├── logger.py                # Per-stage log files + console setup
│   ├── rate_limiter.py          # Async token-bucket rate limiter
│   └── telemetry.py             # Token usage & cost tracking (OpenRouter pricing API)
│
├── intermediate_outputs/        # Auto-created; one JSON per pipeline step
├── output/                      # Auto-created; final Markdown reports
├── docs/                        # Architecture diagrams (.drawio)
└── evaluation/                  # Benchmark & LLM-judge evaluation suite
```

---

## Installation

**Python 3.11+** is required.

```bash
# 1. Clone the repository
git clone <repo-url>
cd Pipetly_Paper/Pipetly

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment variables
cp .env.example .env
# → Edit .env and fill in your API keys (see Configuration below)
```

---

## Configuration

All settings are read from the `.env` file (or environment variables). Only the OpenRouter API key is strictly required; all other keys are optional and the corresponding sources will be skipped gracefully if not provided.

| Variable | Required | Description |
|---|---|---|
| `OPENROUTER_API_KEY` | **Yes** | Your OpenRouter key — used for all LLM calls |
| `LLM_MODEL_GENERAL` | No | Model to use (default: `deepseek/deepseek-v4-flash`) |
| `ELSEVIER_API_KEY` | No | Enables Elsevier / ScienceDirect + Scopus search and full-text |
| `ELSEVIER_INST_TOKEN` | No | Institutional token for Elsevier full-text access |
| `SEMANTIC_SCHOLAR_API_KEY` | No | Higher rate limits for Semantic Scholar |
| `UNPAYWALL_EMAIL` | No | Required for Unpaywall open-access full-text retrieval |
| `NCBI_API_KEY` | No | Higher rate limits for PubMed/PMC |

Key pipeline parameters can also be overridden via environment variable (they match the field names in `config.py`):

| Variable | Default | Description |
|---|---|---|
| `MAX_PAPERS_PER_SOURCE` | `1` | Results fetched per query per API |
| `FULL_TEXT_MIN_CHARS` | `10000` | Minimum accepted full-text length |
| `FULL_TEXT_MAX_CHARS` | `200000` | Maximum accepted full-text length |
| `TOP_K_PROTOCOLS` | `1` | Number of top protocols to include in the final report |
| `LLM_MAX_CONCURRENT` | `20` | Max concurrent LLM calls (Steps 7, 8, 9) |

---

## Usage

```bash
python main.py "your research question or protocol objective"
```

**Example:**
```bash
python main.py "protocol for CRISPR-Cas9 gene editing in human cell lines"
```

The pipeline will:
1. Print progress logs to the console (and per-step log files if `EXPORT_STAGE_LOGS=true`).
2. Write intermediate JSON checkpoints to `intermediate_outputs/`.
3. Save the final Markdown report to `output/`.
4. Print token usage and estimated cost at the end.

**Switching models** without editing `.env`:
```bash
LLM_MODEL_GENERAL=google/gemini-3-flash-preview python main.py "your query"
```

---

## Intermediate Outputs

Each step writes a JSON checkpoint to `intermediate_outputs/`:

| File | Step | Contents |
|---|---|---|
| `step1_expanded_query.json` | 1 | Structured queries + intent extracted from the user prompt |
| `step2_raw_papers.json` | 2 | Raw metadata records from all search APIs |
| `step3_doi_filtered_papers.json` | 3 | Deduplicated papers with a valid DOI |
| `step4_fulltext_raw_papers.json` | 4 | Papers with raw full-text (PDF/XML/HTML) attached |
| `step5_fulltext_clean_papers.json` | 5 | Papers with clean plain text |
| `step6_fulltext_filtered_papers.json` | 6 | Papers passing the length filter |
| `step7_protocols.json` | 7 | Extracted protocol fragments (all depths) |
| `step8_scored_protocols.json` | 8 | Re-scored protocols (score > 60) |
| `test_llm_token_usage.json` | 9 | Per-call token counts + total cost |
| `test_llm_time_usage.json` | 9 | Per-call generation times |

---

## API Clients

**Search APIs** (Step 2 — used for metadata retrieval):

| Client | Source |
|---|---|
| `EuropePMCClient` | Europe PMC |
| `SemanticScholarClient` | Semantic Scholar |
| `ElsevierClient` | Elsevier / ScienceDirect |
| `CrossRefClient` | CrossRef |
| `OpenAlexClient` | OpenAlex |
| `ScopusClient` | Scopus |

**Full-text retrieval APIs** (Step 4 — tried in priority order):

| Client | Format | Notes |
|---|---|---|
| `ElsevierClient` | XML | Open-access XML first |
| `EuropePMCClient` | XML / HTML | |
| `PMCClient` | XML | PubMed Central |
| `SemanticScholarClient` | PDF | |
| `UnpaywallClient` | PDF | Open-access PDFs |
| `OpenAlexClient` | HTML | |

---

## Evaluation

The `evaluation/` directory contains a complete benchmark and automated LLM-as-a-judge suite to compare protocol quality across different models and against reference protocols. See the [Evaluation README](evaluation/README.md) for full details.
