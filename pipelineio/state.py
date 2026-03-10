import pickle
from typing import Any

from .atomic import AtomicSaver
from .uris import normalize_uri


def save_draft(obj: Any, uri: str) -> None:
    path = normalize_uri(uri)
    with AtomicSaver(path, mode="wb") as f:
        pickle.dump(obj, f)


def load_draft(uri: str) -> Any:
    path = normalize_uri(uri)
    with open(path, "rb") as f:
        return pickle.load(f)
