#!/usr/bin/env python
"""
Training Pipeline Runner
- Check if new training data exists
- Prepare data splits  
- Run SFT training (if data is new)
- Evaluate vs baseline
- Ingest & register
"""
import json, os, sys, time
from datetime import datetime

PROJECT_ROOT = r"E:\AI_Workspace\MSS-AI\project"
os.chdir(PROJECT_ROOT)
sys.path.insert(0, os.path.join(PROJECT_ROOT, "mssclaw", "core"))

from training_pipeline import TrainingPipeline, TrainingConfig, EvalConfig, ModelRegistry

RESULTS_DIR = os.path.join(PROJECT_ROOT, "data", "pipeline_runs")
os.makedirs(RESULTS_DIR, exist_ok=True)

def main():
    print("=" * 60)
    print("MSS TRAINING PIPELINE RUNNER")
    print("=" * 60)
    
    # Check what training data is available
    data_candidates = [
        "data/training_pairs.json",
        "prompt-rewrite/data/merged_daily_197.json",
        "data/merged_daily_197.json",
    ]
    
    data_path = None
    for candidate in data_candidates:
        full = os.path.join(PROJECT_ROOT, candidate)
        if os.path.exists(full):
            data_path = candidate
            size_kb = os.path.getsize(full) // 1024
            print(f"\n  📄 Found training data: {candidate} ({size_kb} KB)")
            break
    
    if not data_path:
        print("\n  ⚠️ No training data found — checking prompt-rewrite directory...")
        pr_data = os.path.join(PROJECT_ROOT, "prompt-rewrite", "data")
        if os.path.exists(pr_data):
            for fn in os.listdir(pr_data):
                if fn.endswith('.json'):
                    fpath = os.path.join(pr_data, fn)
                    size_kb = os.path.getsize(fpath) // 1024
                    print(f"    {fn} ({size_kb} KB)")
    
    # Config
    config = TrainingConfig(
        data_path=data_path or "data/training_pairs.json",
        output_dir="data/models",
        epochs=3,
        learning_rate=2e-4,
        lora_rank=16,
    )
    
    eval_config = EvalConfig(
        pass_threshold=0.65,
        test_turns=20,
    )
    
    registry = ModelRegistry(path="data/model_registry.json")
    
    # Run pipeline
    pipeline = TrainingPipeline(
        config=config,
        eval_config=eval_config,
        registry=registry,
        workspace=PROJECT_ROOT,
    )
    
    stages = pipeline.run(force=False)
    
    # Print summary
    print("\n" + "=" * 60)
    print("PIPELINE SUMMARY")
    print("=" * 60)
    for s in stages:
        icon = "✅" if s.status.value == "passed" else "⏭️" if s.status.value == "skipped" else "❌"
        print(f"  {icon} {s.stage.value:<10} {s.status.value:<8} ({s.duration_s:.1f}s)")
        if s.metrics:
            for k, v in s.metrics.items():
                if k != "artifacts":
                    print(f"       {k}: {v}")

if __name__ == "__main__":
    main()
