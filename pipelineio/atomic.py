import os
import tempfile
from pathlib import Path


def atomic_write_bytes(path_str: str, data: bytes) -> None:
    path = Path(path_str)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_path = tempfile.mkstemp(dir=path.parent, prefix="._tmp_atomic_")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
        os.replace(temp_path, path)
    except Exception:
        os.remove(temp_path)
        raise


def atomic_write_text(path_str: str, text: str, encoding: str = "utf-8") -> None:
    atomic_write_bytes(path_str, text.encode(encoding))


class AtomicSaver:
    def __init__(self, path_str: str, mode: str = "wb"):
        self.path = Path(path_str)
        self.mode = mode
        self.temp_path = None
        self.file = None

    def __enter__(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd, temp_path = tempfile.mkstemp(dir=self.path.parent, prefix="._tmp_atomic_saver_")
        self.temp_path = Path(temp_path)
        self.file = os.fdopen(fd, self.mode)
        return self.file

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.file:
            self.file.close()
        if exc_type is not None:
            if self.temp_path and self.temp_path.exists():
                self.temp_path.unlink()
        else:
            if self.temp_path and self.temp_path.exists():
                os.replace(self.temp_path, self.path)
