from urllib.parse import urlparse

def is_http_uri(uri: str) -> bool:
    return uri.startswith("http://") or uri.startswith("https://")

def is_file_uri(uri: str) -> bool:
    return uri.startswith("file://")

def normalize_uri(uri: str) -> str:
    if is_file_uri(uri):
        return urlparse(uri).path
    return uri
