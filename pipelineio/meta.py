from pathlib import Path
from typing import Any

import requests

from .config import PIPELINE_HTTP_TIMEOUT
from .uris import is_http_uri, normalize_uri


def get_input_meta(uri: str) -> dict[str, Any]:
    return _get_meta(uri)


def get_output_meta(uri: str) -> dict[str, Any]:
    return _get_meta(uri)


def _get_meta(uri: str) -> dict[str, Any]:
    if is_http_uri(uri):
        try:
            resp = requests.head(uri, timeout=PIPELINE_HTTP_TIMEOUT)
            return {
                "type": "http",
                "url": uri,
                "status": resp.status_code,
                "etag": resp.headers.get("etag"),
                "last_modified": resp.headers.get("last-modified"),
                "content_length": resp.headers.get("content-length"),
            }
        except Exception as e:
            return {"type": "http", "url": uri, "error": str(e)}

    path_str = normalize_uri(uri)
    path = Path(path_str)
    if path.exists():
        stat = path.stat()
        return {
            "type": "file",
            "path": path_str,
            "exists": True,
            "mtime_ns": stat.st_mtime_ns,
            "size": stat.st_size,
        }
    return {"type": "file", "path": path_str, "exists": False}
