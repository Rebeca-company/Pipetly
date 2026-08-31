"""Evaluation – LLM Judge for protocol quality assessment.

Uses Claude Sonnet 5 via OpenRouter to score
an extracted protocol against 6 metrics (1–5 each):
  Relevance · Completeness · Parameter Consistency ·
  Executability · Structural Coherence · Conciseness

Run as a standalone script to execute the full 3-run benchmark:
    python evaluation/llm_judge.py
    python evaluation/llm_judge.py --data path/to/protocols.json
"""

from __future__ import annotations

import asyncio
import json
import logging
import sys
from pathlib import Path
from typing import Any, Optional

# Add project root to path so standalone execution works
_HERE = Path(__file__).resolve().parent
_EVAL_ROOT = _HERE.parent
_PIPETLY_ROOT = _EVAL_ROOT.parent
if str(_PIPETLY_ROOT) not in sys.path:
    sys.path.insert(0, str(_PIPETLY_ROOT))

import httpx

from config import get_settings
from evaluation.scripts.models import (
    EvaluationEntry,
    JudgeResult,
    MetricScore,
    RunResult,
    SourceResult,
)
from utils.llm_client import BaseLLMProcessor

logger = logging.getLogger(__name__)
_s = get_settings()

JUDGE_MODEL = "anthropic/claude-5-sonnet"

# ── System prompt ─────────────────────────────────────────────────────────────

_SYSTEM_PROMPT = """You are an expert evaluator of laboratory experimental protocols (biology, biochemistry, molecular biology). Your task is to evaluate the quality of an experimental protocol that has been automatically extracted by an AI system from a scientific article.

You are provided with the extracted protocol and the user query that led to its extraction.

IMPORTANT: You do not have access to the original document or to a reference protocol. You must evaluate the provided protocol in a self-contained manner, based on your expert knowledge of what constitutes a complete, coherent, and executable laboratory protocol for the type of technique described.

Evaluate the protocol according to the following 6 metrics, assigning a score from 1 to 5 (decimals are allowed, e.g., 3.5) for each, where:
1 = Very poor
2 = Poor
3 = Acceptable
4 = Good
5 = Excellent

For each metric, provide also a brief justification of your score. The justification for each metric must be a MAXIMUM OF 30 WORDS.

---

METRICS:

1. RELEVANCE
The degree to which the extracted protocol effectively corresponds to the technique, objective, or query requested, without mixing steps from another protocol or deviating toward a technique different from the one requested.
Guiding questions:
- Does the extracted protocol correspond to the technique/objective indicated in the query?
- Have steps belonging to a different protocol been mixed in (e.g., from the same article but from a different experimental section)?
- Does the focus of the protocol remain consistent with what was requested, without deviating toward procedures that were not requested?

Rubric:
1 - The protocol does not correspond at all to the requested technique/objective.
2 - The protocol corresponds partially, but mixes in significant steps from another technique that was not requested.
3 - The protocol corresponds to the requested technique, with some minor, non-critical deviation.
4 - The protocol corresponds to the requested technique, with minimal deviations.
5 - The protocol corresponds exactly to the requested technique/objective, with no mixing or deviation.

2. COMPLETENESS
The degree to which the protocol includes all elements expected for this type of protocol (steps, reagents, equipment, and measurable parameters such as times, temperatures, concentrations, and volumes), according to what a domain expert would consider standard.
Guiding questions:
- Is any step missing that would normally be necessary in a protocol of this type?
- Does each step include the corresponding reagents and equipment?
- Are the relevant measurable parameters present in each step?

Rubric:
1 - Critical steps are missing and/or most reagents, equipment, or parameters are not mentioned.
2 - The main steps are present but several relevant reagents, equipment, or parameters are missing.
3 - Almost all expected elements are present, with some non-critical omission.
4 - All expected elements are present, with very minor omissions.
5 - All expected steps, reagents, equipment, and parameters are present.

3. INTERNAL PARAMETER CONSISTENCY
The degree to which the numerical values and experimental conditions (times, temperatures, concentrations, volumes, units) are coherent with one another throughout the protocol, without contradictions or physicochemically implausible values.
Guiding questions:
- Do numerical values remain consistent every time they are repeated or referenced?
- Are there contradictions between parameters (e.g., a final concentration that does not match the starting volume and concentration)?
- Are the values plausible for the experimental context?

Rubric:
1 - Multiple numerical contradictions and/or physicochemically implausible values.
2 - Several significant inconsistencies between parameters.
3 - Some minor inconsistency that does not compromise overall validity.
4 - Parameters are consistent, with at most one trivial discrepancy.
5 - All numerical values are consistent and plausible throughout the protocol.

4. EXECUTABILITY
The degree to which, given the content present, the instructions are written explicitly and unambiguously enough for a researcher to be able to follow and execute them without needing to interpret, guess, or consult the original document.
Guiding questions:
- Are the instructions for each step clear and actionable as written?
- Are there ambiguities that would force the reader to assume unstated information?
- Could someone at the level of a laboratory researcher execute the protocol using only what is indicated here?

Rubric:
1 - The instructions are vague or ambiguous in most steps; would require constant guessing.
2 - Several steps are ambiguous or depend on subjective interpretation.
3 - Most steps are clear, with some occasional ambiguity.
4 - The instructions are clear and actionable, with minimal ambiguity.
5 - All instructions are explicit, clear, and executable with no need to interpret anything.

5. STRUCTURAL COHERENCE
The degree to which the protocol's steps follow a logical and consistent order, without gaps, contradictions, or broken dependencies between steps.
Guiding questions:
- Are the steps in the correct sequence (e.g., a reagent is not used before it has been prepared)?
- Are there abrupt jumps or a lack of transition between steps?
- Is the internal numbering/organization consistent?

Rubric:
1 - The order of the steps is illogical or there are serious broken dependencies.
2 - There are several gaps or sequencing problems that make the protocol hard to follow.
3 - The structure is mostly logical, with some minor gap or inconsistency.
4 - The structure is logical and consistent, with minimal issues.
5 - The sequence of steps is completely logical, consistent, and free of gaps.

6. CONCISENESS
The absence of noise, redundancy, or irrelevant information that adds no value to the protocol (signal-to-noise ratio).
Guiding questions:
- Is there unnecessarily repeated information?
- Has content been included that does not belong to the protocol itself (discussion, theoretical background, results)?
- Could the text be shortened without losing information relevant to execution?

Rubric:
1 - The protocol contains a lot of noise, redundancy, or content unrelated to the protocol (discussion, results, etc.).
2 - There is notable redundancy or irrelevant content.
3 - There is some noise or repetition, but it does not compromise the usefulness of the protocol.
4 - The protocol is mostly concise, with minimal redundancy.
5 - The protocol is completely concise, with no noise or redundancy.

---

Note on the use of the query: the provided query should be used to verify RELEVANCE (metric 1) and to calibrate your domain expectations for the other metrics (e.g., what technique this is, what steps are expected). Do not evaluate the other metrics based on whether the protocol literally "answers" the query; that judgment belongs solely to the Relevance metric.

For each metric, provide a brief justification of your score. The justification for each metric must be a MAXIMUM OF 30 WORDS.

Evaluate the provided protocol and return your evaluation strictly following the provided schema."""

# ── Structured output schema (OpenAI tool-use format) ─────────────────────────

_JUDGE_SCHEMA = {
    "type": "function",
    "function": {
        "name": "protocol_evaluation",
        "description": "Evaluation of an extracted experimental protocol according to 6 quality metrics, each scored from 1 to 5.",
        "parameters": {
            "type": "object",
        "properties": {
            "relevance": {
                "type": "object",
                "properties": {
                    "score": {"type": "number", "minimum": 1, "maximum": 5, "description": "Relevance score (1-5)"},
                    "justification": {"type": "string", "description": "Maximum 30 words explaining the relevance score"},
                },
                "required": ["score", "justification"],
            },
            "completeness": {
                "type": "object",
                "properties": {
                    "score": {"type": "number", "minimum": 1, "maximum": 5, "description": "Completeness score (1-5)"},
                    "justification": {"type": "string", "description": "Maximum 30 words explaining the completeness score"},
                },
                "required": ["score", "justification"],
            },
            "parameter_consistency": {
                "type": "object",
                "properties": {
                    "score": {"type": "number", "minimum": 1, "maximum": 5, "description": "Internal parameter consistency score (1-5)"},
                    "justification": {"type": "string", "description": "Maximum 30 words explaining the parameter consistency score"},
                },
                "required": ["score", "justification"],
            },
            "executability": {
                "type": "object",
                "properties": {
                    "score": {"type": "number", "minimum": 1, "maximum": 5, "description": "Executability score (1-5)"},
                    "justification": {"type": "string", "description": "Maximum 30 words explaining the executability score"},
                },
                "required": ["score", "justification"],
            },
            "structural_coherence": {
                "type": "object",
                "properties": {
                    "score": {"type": "number", "minimum": 1, "maximum": 5, "description": "Structural coherence score (1-5)"},
                    "justification": {"type": "string", "description": "Maximum 30 words explaining the structural coherence score"},
                },
                "required": ["score", "justification"],
            },
            "conciseness": {
                "type": "object",
                "properties": {
                    "score": {"type": "number", "minimum": 1, "maximum": 5, "description": "Conciseness score (1-5)"},
                    "justification": {"type": "string", "description": "Maximum 30 words explaining the conciseness score"},
                },
                "required": ["score", "justification"],
            },
        },
            "required": [
                "relevance",
                "completeness",
                "parameter_consistency",
                "executability",
                "structural_coherence",
                "conciseness",
            ],
        },
    }
}


# ── Processor class ───────────────────────────────────────────────────────────


class ProtocolJudge(BaseLLMProcessor):
    """LLM judge that scores one (query, protocol) pair across 6 quality metrics.

    Follows the same structure as pipeline processors in ``processors/``:
    extends :class:`BaseLLMProcessor`, uses a private system prompt and schema,
    and exposes a single async entry-point method (``judge``).
    """

    def __init__(self, max_concurrent: int = 5) -> None:
        super().__init__("eval")
        self._semaphore = asyncio.Semaphore(max_concurrent)

    async def judge(
        self,
        query: str,
        protocol_text: str,
        http_client: Optional[httpx.AsyncClient] = None,
    ) -> JudgeResult:
        """Evaluate one protocol and return structured 6-metric scores."""
        async with self._semaphore:
            for attempt in range(1, 4):
                try:
                    return await self._call_once(query, protocol_text, http_client)
                except Exception as exc:  # noqa: BLE001
                    if attempt == 3:
                        raise
                    wait = 2.0 ** (attempt - 1)
                    logger.warning(
                        "Judge attempt %d/3 failed: %s – retrying in %.1fs",
                        attempt, exc, wait,
                    )
                    await asyncio.sleep(wait)

    async def judge_all(
        self,
        entries: list[EvaluationEntry],
        run_number: int,
    ) -> RunResult:
        """Evaluate all (entry, source) pairs in one run concurrently.

        Sources are discovered dynamically from each entry's ``protocols`` dict,
        so any number of models can be added without changing this code.
        """
        jobs = [
            (entry, src, text)
            for entry in entries
            for src, text in entry.protocols.items()
            if text.strip() and "PLACEHOLDER" not in text
        ]

        async with httpx.AsyncClient(
            timeout=_s.http_timeout * 4,
            limits=httpx.Limits(max_keepalive_connections=10, max_connections=20),
        ) as client:
            outcomes = await asyncio.gather(
                *[self.judge(entry.query, text, client) for entry, src, text in jobs],
                return_exceptions=True,
            )

        results: list[SourceResult] = []
        for (entry, src, _), outcome in zip(jobs, outcomes):
            if isinstance(outcome, Exception):
                logger.warning("[%s] %s FAILED: %s", entry.id, src, outcome)
                results.append(
                    SourceResult(entry_id=entry.id, source=src, run=run_number, error=str(outcome))
                )
            else:
                logger.info(
                    "[%s] %-15s mean=%.2f | rel=%d cmp=%d par=%d exe=%d str=%d con=%d",
                    entry.id, src, outcome.mean_score,
                    outcome.relevance.score, outcome.completeness.score,
                    outcome.parameter_consistency.score, outcome.executability.score,
                    outcome.structural_coherence.score, outcome.conciseness.score,
                )
                results.append(
                    SourceResult(entry_id=entry.id, source=src, run=run_number, result=outcome)
                )

        return RunResult(run=run_number, results=results)

    # ── Internal ──────────────────────────────────────────────────────────────

    async def _call_once(
        self,
        query: str,
        protocol_text: str,
        http_client: Optional[httpx.AsyncClient],
    ) -> JudgeResult:
        payload: dict[str, Any] = {
            "model": JUDGE_MODEL,
            "temperature": 0.1,
            "messages": [
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": f"QUERY:\n{query}\n\nPROTOCOL TO EVALUATE:\n{protocol_text}"},
            ],
            "tools": [_JUDGE_SCHEMA],
            "tool_choice": {"type": "function", "function": {"name": _JUDGE_SCHEMA["function"]["name"]}},
        }

        if http_client is not None:
            resp = await http_client.post(
                f"{self._base}/chat/completions", json=payload, headers=self._headers
            )
        else:
            async with httpx.AsyncClient(timeout=_s.http_timeout * 4) as client:
                resp = await client.post(
                    f"{self._base}/chat/completions", json=payload, headers=self._headers
                )

        if resp.is_error:
            logger.error("OpenRouter %s – %s", resp.status_code, resp.text[:400])
            resp.raise_for_status()

        raw = resp.json()
        self._record_llm_usage(raw)
        return self._parse_response(raw)

    def _parse_response(self, raw: dict[str, Any]) -> JudgeResult:
        message = (raw.get("choices") or [{}])[0].get("message", {})
        tool_calls = message.get("tool_calls") or []
        data: dict[str, Any] = {}

        if tool_calls:
            try:
                args = tool_calls[0].get("function", {}).get("arguments", "{}")
                data = json.loads(args)
            except json.JSONDecodeError:
                pass

        if not data:
            content = message.get("content") or ""
            if isinstance(content, str) and content.strip():
                try:
                    data = json.loads(content)
                except json.JSONDecodeError:
                    pass

        if not data:
            raise ValueError(f"Empty judge response: {str(message)[:300]}")

        return JudgeResult(
            relevance=MetricScore(**data["relevance"]),
            completeness=MetricScore(**data["completeness"]),
            parameter_consistency=MetricScore(**data["parameter_consistency"]),
            executability=MetricScore(**data["executability"]),
            structural_coherence=MetricScore(**data["structural_coherence"]),
            conciseness=MetricScore(**data["conciseness"]),
        )


# ── Stand-alone entry point ───────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse
    import argparse
    from datetime import datetime

    from utils.logger import setup_logging

    setup_logging()

    N_RUNS = 1
    _DEFAULT_DATA = _EVAL_ROOT / "benchmark" / "cases.json"
    _DEFAULT_OUT  = _EVAL_ROOT / "results"

    parser = argparse.ArgumentParser(description="Run the LLM-judge evaluation benchmark.")
    parser.add_argument("--data", type=Path, default=_DEFAULT_DATA)
    parser.add_argument("--out",  type=Path, default=_DEFAULT_OUT)
    args = parser.parse_args()

    async def _main() -> None:
        data_path: Path = args.data
        if not data_path.exists():
            raise FileNotFoundError(f"Benchmark data not found: {data_path}")

        raw = json.loads(data_path.read_text(encoding="utf-8"))
        entries = [EvaluationEntry.model_validate(item) for item in raw]
        all_sources = sorted({src for e in entries for src in e.protocols})
        logger.info(
            "[Eval] Loaded %d entries | %d sources | %d runs | judge=%s",
            len(entries), len(all_sources), N_RUNS, JUDGE_MODEL,
        )

        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        run_dir: Path = args.out / ts
        run_dir.mkdir(parents=True, exist_ok=True)

        judge = ProtocolJudge()
        all_runs: list[RunResult] = []

        for run_n in range(1, N_RUNS + 1):
            logger.info("[Eval] START run %d / %d", run_n, N_RUNS)
            rr = await judge.judge_all(entries, run_n)
            all_runs.append(rr)
            logger.info("[Eval] DONE  run %d / %d", run_n, N_RUNS)

        output = {
            "judge_model": JUDGE_MODEL,
            "n_runs": N_RUNS,
            "n_entries": len(entries),
            "runs": [rr.model_dump() for rr in all_runs],
        }
        out_path = run_dir / "scores_raw.json"
        out_path.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")
        logger.info("[Eval] Results → %s", out_path)


        # Generate Markdown summary
        md_lines = ["# LLM Judge Evaluation Report", f"**Model**: {JUDGE_MODEL} | **Runs**: {N_RUNS} | **Entries**: {len(entries)}\n"]
        md_lines.append("## Average Scores per Source")
        
        from collections import defaultdict
        # source -> metric -> list of scores
        src_scores = defaultdict(lambda: defaultdict(list))
        # entry_id -> source -> run -> JudgeResult
        detailed_results = defaultdict(lambda: defaultdict(dict))
        
        for rr in all_runs:
            for sr in rr.results:
                if sr.result:
                    src_scores[sr.source]["mean"].append(sr.result.mean_score)
                    src_scores[sr.source]["relevance"].append(sr.result.relevance.score)
                    src_scores[sr.source]["completeness"].append(sr.result.completeness.score)
                    src_scores[sr.source]["parameter_consistency"].append(sr.result.parameter_consistency.score)
                    src_scores[sr.source]["executability"].append(sr.result.executability.score)
                    src_scores[sr.source]["structural_coherence"].append(sr.result.structural_coherence.score)
                    src_scores[sr.source]["conciseness"].append(sr.result.conciseness.score)
                    detailed_results[sr.entry_id][sr.source][rr.run] = sr.result
        
        md_lines.append("| Source | Mean | Rel | Cmp | Par | Exe | Str | Con |")
        md_lines.append("|---|---|---|---|---|---|---|---|")
        for src, metrics in src_scores.items():
            avg = {m: sum(v)/len(v) for m, v in metrics.items()}
            md_lines.append(f"| **{src}** | {avg['mean']:.2f} | {avg['relevance']:.1f} | {avg['completeness']:.1f} | {avg['parameter_consistency']:.1f} | {avg['executability']:.1f} | {avg['structural_coherence']:.1f} | {avg['conciseness']:.1f} |")
        
        md_lines.append("\n## Detailed Justifications (Run 1)\n")
        for entry_id in sorted(detailed_results.keys()):
            md_lines.append(f"### Entry: {entry_id}")
            for src in sorted(detailed_results[entry_id].keys()):
                md_lines.append(f"#### Source: {src}")
                res = detailed_results[entry_id][src].get(1) # Get run 1
                if res:
                    md_lines.append(f"- **Relevance ({res.relevance.score}/5):** {res.relevance.justification}")
                    md_lines.append(f"- **Completeness ({res.completeness.score}/5):** {res.completeness.justification}")
                    md_lines.append(f"- **Parameter Consistency ({res.parameter_consistency.score}/5):** {res.parameter_consistency.justification}")
                    md_lines.append(f"- **Executability ({res.executability.score}/5):** {res.executability.justification}")
                    md_lines.append(f"- **Structural Coherence ({res.structural_coherence.score}/5):** {res.structural_coherence.justification}")
                    md_lines.append(f"- **Conciseness ({res.conciseness.score}/5):** {res.conciseness.justification}\n")
                else:
                    md_lines.append("*No data for Run 1.*\n")
        
        md_path = run_dir / "scores_summary.md"
        md_path.write_text("\n".join(md_lines), encoding="utf-8")
        logger.info("[Eval] Summary → %s", md_path)

        events = judge.get_llm_token_events()
        logger.info("[Eval] LLM calls=%d", len(events))

    asyncio.run(_main())
