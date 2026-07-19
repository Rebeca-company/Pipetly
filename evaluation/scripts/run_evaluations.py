"""Benchmark runner – orchestrates all case × model combinations.

Run from the project root (where main.py lives)::

    python evaluation/scripts/run_evaluations.py

Outputs are saved to evaluation/runs/<case_id>_<model>/.
"""
import json
import os
import shutil
import subprocess
import glob
from pathlib import Path

def get_latest_file(directory, extension):
    files = glob.glob(os.path.join(directory, f"*{extension}"))
    if not files:
        return None
    return max(files, key=os.path.getmtime)

def save_run(case_id, model_id, run_dir):
    run_dir.mkdir(parents=True, exist_ok=True)
    
    # 1. Get latest MD output
    latest_md = get_latest_file("output", ".md")
    if latest_md:
        dest_md = run_dir / f"{case_id}_final_output.md"
        shutil.copy2(latest_md, dest_md)
        print(f"  Copied {latest_md} -> {dest_md}")
    else:
        print("  Warning: No .md file found in output/")

    # 2. Copy ALL intermediate JSON files
    for src in Path("intermediate_outputs").glob("*.json"):
        dest = run_dir / src.name
        shutil.copy2(src, dest)
        
    print(f"  Copied all .json files from intermediate_outputs/")

    # 3. Copy telemetry directory
    telemetry_src = Path("intermediate_outputs/telemetry")
    if telemetry_src.exists():
        telemetry_dest = run_dir / "telemetry"
        if telemetry_dest.exists():
            shutil.rmtree(telemetry_dest)
        shutil.copytree(telemetry_src, telemetry_dest)
        print(f"  Copied telemetry directory")

def main():
    # Load cases from JSON
    benchmark_file = Path(__file__).resolve().parent.parent / "benchmark" / "cases.json"
    if not benchmark_file.exists():
        print(f"Error: Could not find {benchmark_file}")
        return

    with open(benchmark_file, "r", encoding="utf-8") as f:
        cases = json.load(f)

    models = [
        "google/gemini-3-flash-preview",
        "deepseek/deepseek-v4-flash",
        "xiaomi/mimo-v2.5"
    ]

    print(f"Found {len(cases)} cases and {len(models)} models to evaluate.")
    print("=" * 60)

    for case in cases:
        case_id = case["id"]
        query = case["query"]
        
        for model in models:
            # Clean model name for folder (e.g. "google/gemini-3-flash" -> "gemini-3-flash")
            clean_model = model.split("/")[-1]
            run_dir = Path("evaluation/runs") / f"{case_id}_{clean_model}"
            
            # Check if this combination already finished successfully
            if run_dir.exists() and len(list(run_dir.glob("*.md"))) > 0:
                print(f"⏭️  Skipping Case: {case_id} | Model: {model} (Already completed)")
                continue
            
            print(f"\n>>> Running Case: {case_id} | Model: {model} <<<")
            
            # Setup environment variable to override config
            env = os.environ.copy()
            env["LLM_MODEL_GENERAL"] = model
            
            # Run the main pipeline
            try:
                subprocess.run(
                    ["python", "main.py", query],
                    env=env,
                    check=True
                )
                print(f"Pipeline finished successfully. Saving outputs...")
                save_run(case_id, clean_model, run_dir)
                print(f"[DONE] Saved to {run_dir}")
                
            except subprocess.CalledProcessError as e:
                print(f"Error running pipeline for {case_id} with {model}: {e}")
            except Exception as e:
                print(f"Unexpected error: {e}")

if __name__ == "__main__":
    if not Path("main.py").exists():
        print("Please run this script from the project root (where main.py is).")
        print("Example: python evaluation/run_evaluations.py")
    else:
        main()
