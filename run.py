import json
from pathlib import Path
from pipeline.run_logic.ast_runner import discover_and_run_pipeline

if __name__ == "__main__":
    config_path = Path("pipeline_config.json")
    
    # Load config dynamically from file if it exists, otherwise pass an empty dict for AST generation
    if config_path.exists():
        with open(config_path, "r", encoding="utf-8") as f:
            PIPELINE_CONFIG = json.load(f)
    else:
        PIPELINE_CONFIG = {}
        
    discover_and_run_pipeline(PIPELINE_CONFIG)
