import os
from pathlib import Path

PIPELINE_HTTP_TIMEOUT = int(os.environ.get("PIPELINE_HTTP_TIMEOUT", "10"))
PIPELINE_CACHE_DIR = Path(os.environ.get("PIPELINE_CACHE_DIR", ".cache"))
