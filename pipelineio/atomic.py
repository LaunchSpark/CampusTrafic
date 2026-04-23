import os
import tempfile
import time
from pathlib import Path


def _safe_replace(src: Path, dst: Path, retries: int = 5, delay: float = 0.2) -> None:
    last_err = None
    for _ in range(retries):
        try:
            os.replace(str(src), str(dst))
            return
        except PermissionError as e:
            last_err = e
            time.sleep(delay)
    raise last_err


def atomic_write_bytes(path_str: str, data: bytes) -> None:
    path = Path(path_str).resolve()
    path.parent.mkdir(parents=True, exist_ok=True)

    fd, temp_path = tempfile.mkstemp(dir=str(path.parent), prefix="._tmp_atomic_")
    temp_path = Path(temp_path)

    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        _safe_replace(temp_path, path)
    except Exception:
        try:
            if temp_path.exists():
                temp_path.unlink()
        except Exception:
            pass
        raise


def atomic_write_text(path_str: str, text: str, encoding: str = "utf-8") -> None:
    atomic_write_bytes(path_str, text.encode(encoding))


class AtomicSaver:
    def __init__(self, path_str: str, mode: str = "wb"):
        self.path = Path(path_str).resolve()
        self.mode = mode
        self.temp_path = None
        self.file = None

    def __enter__(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd, temp_path = tempfile.mkstemp(
            dir=str(self.path.parent),
            prefix="._tmp_atomic_saver_"
        )
        self.temp_path = Path(temp_path)
        self.file = os.fdopen(fd, self.mode)
        return self.file

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.file and not self.file.closed:
            self.file.flush()
            os.fsync(self.file.fileno())
            self.file.close()

        if exc_type is not None:
            try:
                if self.temp_path and self.temp_path.exists():
                    self.temp_path.unlink()
            except Exception:
                pass
            return False

        try:
            if self.temp_path and self.temp_path.exists():
                _safe_replace(self.temp_path, self.path)
        except Exception:
            try:
                if self.temp_path and self.temp_path.exists():
                    self.temp_path.unlink()
            except Exception:
                pass
            raise

        return False