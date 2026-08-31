"""Extracts Pipetly protocol outputs from run .md files and stores them in
benchmark/cases.json under the ``pipetly_<model>`` key.

Also reads benchmark/reference_outputs/case_XXX.md files and populates the
``gemini_pro`` key with their full content.

Run from the project root::

    python evaluation/scripts/update_protocols.py
"""
import json
from pathlib import Path

_HERE = Path(__file__).resolve().parent          # evaluation/scripts/
_EVAL_ROOT = _HERE.parent                         # evaluation/
_BENCHMARK = _EVAL_ROOT / "benchmark"
_REF_OUTPUTS = _BENCHMARK / "reference_outputs"
_RUNS_DIR = _EVAL_ROOT / "runs"
_CASES_FILE = _BENCHMARK / "cases.json"


def extract_pipetly_protocol(md_path: Path) -> str:
    """Extract the '### Protocol Steps' section from a Pipetly output .md file."""
    content = md_path.read_text(encoding="utf-8")
    lines = content.split("\n")

    start_idx = -1
    for i, line in enumerate(lines):
        if line.strip() == "### Protocol Steps":
            start_idx = i + 1
            break

    if start_idx == -1:
        return ""

    end_idx = len(lines)
    for i in range(start_idx, len(lines)):
        s = lines[i].strip()
        if (
            s.startswith("## Rank")
            or s.startswith("### Inherited")
            or s.lower().startswith("**citations**")
        ):
            end_idx = i
            break

    return "\n".join(lines[start_idx:end_idx]).strip()


def extract_reference_protocol(md_path: Path) -> str:
    """Return the full text of a reference output .md (Gemini-generated)."""
    return md_path.read_text(encoding="utf-8").strip()


def main() -> None:
    if not _CASES_FILE.exists():
        print(f"Error: {_CASES_FILE} not found.")
        return

    cases = json.loads(_CASES_FILE.read_text(encoding="utf-8"))

    for case in cases:
        case_id = case["id"]
        protocols_dict = case.get("protocols", {})

        # ── 1. Remove stale placeholder keys ───────────────────────────────
        for k in [k for k in protocols_dict if k.startswith("pipetly_model")]:
            del protocols_dict[k]

        # ── 2a. Populate gemini_pro from reference_outputs/Gemini_Pro/case_XXX.txt ──────
        ref_file_pro = _REF_OUTPUTS / "Gemini_Pro" / f"{case_id}.txt"
        if ref_file_pro.exists():
            ref_text = extract_reference_protocol(ref_file_pro)
            if ref_text:
                protocols_dict["gemini_pro"] = ref_text
                print(f"  [{case_id}] gemini_pro <- Gemini_Pro/{case_id}.txt")
            else:
                print(f"  [{case_id}] Warning: reference file is empty: {ref_file_pro.name}")
        else:
            print(f"  [{case_id}] Warning: no reference file found at {ref_file_pro}")

        # ── 2b. Populate geminideepresearch from reference_outputs/Gemini_DeepResearch/case_XXX.md ──────
        ref_file_dr = _REF_OUTPUTS / "Gemini_DeepResearch" / f"{case_id}.md"
        if ref_file_dr.exists():
            ref_text = extract_reference_protocol(ref_file_dr)
            if ref_text:
                protocols_dict["geminideepresearch"] = ref_text
                print(f"  [{case_id}] geminideepresearch <- Gemini_DeepResearch/{case_id}.md")
            else:
                print(f"  [{case_id}] Warning: reference file is empty: {ref_file_dr.name}")
        else:
            print(f"  [{case_id}] Warning: no reference file found at {ref_file_dr}")

        # ── 3. Populate pipetly_<model> from runs/<case_id>_<model>/ ───────
        for run_dir in sorted(_RUNS_DIR.glob(f"{case_id}_*")):
            if not run_dir.is_dir():
                continue

            model_name = run_dir.name.replace(f"{case_id}_", "")
            md_file = run_dir / "final_output.md"

            if md_file.exists():
                protocol_text = extract_pipetly_protocol(md_file)
                if protocol_text:
                    key = f"pipetly_{model_name}"
                    protocols_dict[key] = protocol_text
                    print(f"  [{case_id}] {key} <- runs/{run_dir.name}/final_output.md")
                else:
                    print(f"  [{case_id}] Warning: '### Protocol Steps' not found in {md_file}")
            else:
                print(f"  [{case_id}] Warning: final_output.md not found in {run_dir.name}")

        # ── 4. Reorder keys according to requested priority ────────────────────
        ordered_protocols = {}
        
        if "benchmark" in protocols_dict:
            ordered_protocols["benchmark"] = protocols_dict["benchmark"]
        if "gemini_pro" in protocols_dict:
            ordered_protocols["gemini_pro"] = protocols_dict["gemini_pro"]
        if "geminideepresearch" in protocols_dict:
            ordered_protocols["geminideepresearch"] = protocols_dict["geminideepresearch"]
            
        # Add pipetly models in order: gemini, deepseek, mimo
        for k in sorted(protocols_dict.keys()):
            if k.startswith("pipetly_gemini"):
                ordered_protocols[k] = protocols_dict[k]
        for k in sorted(protocols_dict.keys()):
            if k.startswith("pipetly_deepseek"):
                ordered_protocols[k] = protocols_dict[k]
        for k in sorted(protocols_dict.keys()):
            if k.startswith("pipetly_mimo"):
                ordered_protocols[k] = protocols_dict[k]
                
        # Add any other leftover keys
        for k in protocols_dict:
            if k not in ordered_protocols:
                ordered_protocols[k] = protocols_dict[k]

        case["protocols"] = ordered_protocols

    _CASES_FILE.write_text(json.dumps(cases, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nUpdated {_CASES_FILE} successfully.")


if __name__ == "__main__":
    main()
