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
│     (processors/)           │  (Boolean/MeSH) and semantic queries (NL sentences)
└────────────┬────────────────┘
             │
             ▼
┌─────────────────────────────┐
│  2. Multi-Source Fetch      │  Concurrent async calls to:
│     (processors/            │   • Europe PMC   • Semantic Scholar
│      orchestrator.py)       │   • Elsevier     • CrossRef
│                             │   • OpenAlex
└────────────┬────────────────┘
             │
             ▼
┌─────────────────────────────┐
│  3. Full-Text Filter        │  Drops: papers without full text or without a
│     (processors/            │  Methods/Experimental section (Regex)
│      full_text_filter.py)   │
└────────────┬────────────────┘
             │
             ▼
┌─────────────────────────────┐
│  4. Recursive Extraction    │  Gemini parses each paper → structured JSON steps
│     "Citation Investigator" │  If a step cites another paper (e.g. "[14]"),
│     (processors/            │  that reference is resolved, fetched, and re-parsed
│      protocol_extractor.py) │  (up to 3 levels deep)
└────────────┬────────────────┘
             │
             ▼
┌─────────────────────────────┐
│  5. Scoring & Output        │  Gemini scores each protocol against the original
│     (processors/scorer.py)  │  intent → top-K results written to Markdown
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
│   └── protocol.py           → ProtocolStep, ExtractedProtocol, ScoredProtocol
│
├── api_clients/              ← Async httpx wrappers (one file per source)
│   ├── base.py               → Shared retry logic & token-bucket rate limiter
│   ├── europe_pmc.py
│   ├── semantic_scholar.py
│   ├── elsevier.py
│   ├── crossref.py
│   └── openalex.py
│
├── processors/               ← Pipeline stages
│   ├── query_expander.py     → Stage 1
│   ├── orchestrator.py       → Stage 2
│   ├── full_text_filter.py   → Stage 3
│   ├── protocol_extractor.py → Stage 4
│   └── scorer.py             → Stage 5
│
└── utils/
    ├── rate_limiter.py       → Async token-bucket rate limiter
    └── output_formatter.py   → Markdown report writer
```

---

## Requirements

- Python 3.11+
- A [conda](https://docs.conda.io/) environment named `pipetly` (or any venv)
- An [OpenRouter](https://openrouter.ai/) API key (used to call Gemini 1.5 Flash)

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

Optional pipeline tunables (add to `.env` to override defaults):

| Variable | Default | Description |
|---|---|---|
| `MAX_PAPERS_PER_SOURCE` | `10` | Results fetched per API per query |
| `MAX_CITATION_DEPTH` | `3` | Max recursive citation-resolution depth |
| `TOP_K_PROTOCOLS` | `3` | Number of protocols to score and include in the report |
| `HTTP_TIMEOUT` | `30.0` | Per-request timeout in seconds |
| `HTTP_MAX_RETRIES` | `4` | Max retries on rate-limit / connection errors |

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
**Relevance score:** 0.94
...

### Protocol Steps

**Step 1.** Design sgRNA targeting the gene of interest using an online tool (e.g. Benchling).
- *Reagents:* sgRNA oligos, T4 PNK buffer
...
```

---

## Architecture notes

- **Decoupled layers** — `models/` ↦ `api_clients/` ↦ `processors/` ↦ `utils/`; no circular imports.
- **Async throughout** — `httpx.AsyncClient` + `asyncio.gather` for concurrent multi-source fan-out.
- **Rate limiting** — each API client has its own `RateLimiter` (token-bucket); 429 responses trigger exponential backoff.
- **Citation Investigator** — if an extracted step defers to another paper (`"as described in [14]"`), Pipetly resolves the citation key to a DOI via the bibliography, fetches that paper's full text, and recursively re-extracts the missing details.
- **Graceful degradation** — missing API keys silently skip that source; network errors are logged and the pipeline continues.

---

## License

See [LICENSE](LICENSE).
