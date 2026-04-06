from __future__ import annotations

"""Generate auxiliary Step 4 attempt telemetry without modifying pipeline code.

This script reconstructs per-attempt telemetry from existing intermediates:
- step3_doi_filtered_papers.json (papers entering Step 4)
- step4_fulltext_raw_papers.json (papers with successful full-text retrieval)

Outputs are written to the notebooks folder:
- step4_attempt_telemetry.csv
- step4_attempt_telemetry.json
- step4_attempt_telemetry_summary.csv

Important limitation:
Step 4 currently persists timing only for the winning client (ft_retrieved_by).
For non-winning attempts, timing/error are not persisted, so this script labels
those attempts with inferred statuses.
"""

import json
import re
from pathlib import Path
from typing import Any

import pandas as pd

# Same client priority used in FullTextRetriever._CLIENT_ORDER
CLIENT_ORDER = [
    "elsevier",
    "europe_pmc",
    "pmc",
    "semantic_scholar",
    "unpaywall",
    "openalex",
]

DISPLAY = {
    "elsevier": "Elsevier",
    "europe_pmc": "Europe PMC",
    "pmc": "PMC",
    "semantic_scholar": "Semantic Scholar",
    "unpaywall": "Unpaywall",
    "openalex": "OpenAlex",
}

PMCID_RE = re.compile(r"PMC\d+", re.IGNORECASE)


def _load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def _dedup_key(paper: dict[str, Any]) -> str:
    doi = (paper.get("doi") or "").strip().lower()
    if doi:
        return f"doi:{doi}"
    url = (paper.get("url") or "").strip()
    if url:
        m = PMCID_RE.search(url)
        if m:
            return f"pmcid:{m.group(0).upper()}"
    title = (paper.get("title") or "").strip().lower()
    return f"title:{title}" if title else "unknown"


def build_attempt_telemetry(step3: list[dict[str, Any]], step4: list[dict[str, Any]]) -> pd.DataFrame:
    # Keep one representative per dedup key, matching Step 4's dedup fetch behavior.
    step3_by_key: dict[str, dict[str, Any]] = {}
    for p in step3:
        key = _dedup_key(p)
        if key not in step3_by_key:
            step3_by_key[key] = p

    step4_by_key: dict[str, dict[str, Any]] = {}
    for p in step4:
        key = _dedup_key(p)
        if key not in step4_by_key:
            step4_by_key[key] = p

    rows: list[dict[str, Any]] = []
    for key, p3 in step3_by_key.items():
        p4 = step4_by_key.get(key)

        winner = None
        winner_ms = None
        if p4 is not None:
            winner = (p4.get("ft_retrieved_by") or "").strip().lower() or None
            winner_ms = p4.get("ft_response_time_ms")

        for i, client in enumerate(CLIENT_ORDER):
            if winner is None:
                status = "attempted_no_success_unlogged"
                elapsed_ms = None
                is_error = None
            else:
                winner_idx = CLIENT_ORDER.index(winner) if winner in CLIENT_ORDER else None
                if client == winner:
                    status = "success"
                    elapsed_ms = winner_ms
                    is_error = False
                elif winner_idx is not None and i < winner_idx:
                    status = "attempted_before_success_unlogged"
                    elapsed_ms = None
                    is_error = None
                else:
                    status = "not_attempted_after_success"
                    elapsed_ms = None
                    is_error = None

            rows.append(
                {
                    "paper_key": key,
                    "doi": p3.get("doi"),
                    "title": p3.get("title"),
                    "source_api": p3.get("source"),
                    "client": client,
                    "client_label": DISPLAY.get(client, client),
                    "attempt_order": i + 1,
                    "status": status,
                    "elapsed_ms": elapsed_ms,
                    "is_error": is_error,
                }
            )

    return pd.DataFrame(rows)


def build_summary(df_attempts: pd.DataFrame) -> pd.DataFrame:
    summary = (
        df_attempts.groupby("client_label", dropna=False)
        .agg(
            attempts_total=("status", "count"),
            success=("status", lambda s: int((s == "success").sum())),
            attempted_before_success_unlogged=("status", lambda s: int((s == "attempted_before_success_unlogged").sum())),
            attempted_no_success_unlogged=("status", lambda s: int((s == "attempted_no_success_unlogged").sum())),
            not_attempted_after_success=("status", lambda s: int((s == "not_attempted_after_success").sum())),
            mean_success_ms=("elapsed_ms", "mean"),
            median_success_ms=("elapsed_ms", "median"),
            total_success_ms=("elapsed_ms", "sum"),
        )
        .reset_index()
        .sort_values(["total_success_ms", "success"], ascending=[False, False])
    )
    return summary


def main() -> None:
    repo_root = Path(__file__).resolve().parent.parent
    io_dir = repo_root / "intermediate_outputs"
    out_dir = Path(__file__).resolve().parent

    step3_path = io_dir / "step3_doi_filtered_papers.json"
    if not step3_path.exists():
        step3_path = io_dir / "step3_filtered_papers.json"

    step4_path = io_dir / "step4_fulltext_raw_papers.json"

    if not step3_path.exists() or not step4_path.exists():
        missing = [str(p) for p in [step3_path, step4_path] if not p.exists()]
        raise FileNotFoundError(f"Missing required intermediate files: {missing}")

    step3 = _load_json(step3_path)
    step4 = _load_json(step4_path)

    if not isinstance(step3, list) or not isinstance(step4, list):
        raise ValueError("Expected list JSON payloads for step3/step4 files.")

    attempts = build_attempt_telemetry(step3, step4)
    summary = build_summary(attempts)

    csv_path = out_dir / "step4_attempt_telemetry.csv"
    json_path = out_dir / "step4_attempt_telemetry.json"
    summary_csv_path = out_dir / "step4_attempt_telemetry_summary.csv"

    attempts.to_csv(csv_path, index=False, encoding="utf-8")
    attempts.to_json(json_path, orient="records", force_ascii=False, indent=2)
    summary.to_csv(summary_csv_path, index=False, encoding="utf-8")

    print(f"Step 3 records            : {len(step3)}")
    print(f"Step 4 successful records : {len(step4)}")
    print(f"Attempt rows generated    : {len(attempts)}")
    print(f"Saved: {csv_path}")
    print(f"Saved: {json_path}")
    print(f"Saved: {summary_csv_path}")
    print("\nNote: Non-winning attempts are inferred because Step 4 does not persist per-attempt timing/error.")


if __name__ == "__main__":
    main()
