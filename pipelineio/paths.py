from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_ROOT = REPO_ROOT / "data"
RAW_DATA = DATA_ROOT / "raw"
PROCESSED_DATA = DATA_ROOT / "processed"
ARTIFACTS = DATA_ROOT / "artifacts"
RUNS_DIR = ARTIFACTS / "runs"
WORLD_DRAFTS_DIR = ARTIFACTS / "world_drafts"
