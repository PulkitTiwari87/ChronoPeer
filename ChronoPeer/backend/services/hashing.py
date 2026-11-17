"""SHA-256 helpers. A match proves the stored bytes equal the recorded digest when rechecked;
it does not prove the evidence was authentic or that custody was unbroken."""
import hashlib
from pathlib import Path


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path, chunk: int = 65536) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(chunk), b""):
            h.update(block)
    return h.hexdigest()


def verify_stored(path: Path, expected: str) -> str:
    """Return MATCH, MISMATCH or MISSING for a stored evidence file."""
    p = Path(path)
    if not p.is_file():
        return "MISSING"
    return "MATCH" if sha256_file(p) == expected else "MISMATCH"
