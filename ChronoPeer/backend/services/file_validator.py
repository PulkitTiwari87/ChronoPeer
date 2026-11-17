"""Upload validation: filename, extension, size and content checks. Touches no database."""
from dataclasses import dataclass

from . import TooLarge, ValidationFailed

ALLOWED = {".csv": "CSV", ".json": "JSON"}
_BACKSLASH = chr(92)
_FORBIDDEN = ("/", _BACKSLASH, chr(0))


@dataclass(frozen=True)
class Upload:
    filename: str
    file_type: str
    text: str
    size: int


def safe_filename(raw) -> str:
    name = (raw or "").strip()
    if not name or len(name) > 255:
        raise ValidationFailed("Filename is missing or longer than 255 characters")
    if any(c in name for c in _FORBIDDEN) or ".." in name or any(ord(c) < 32 for c in name):
        raise ValidationFailed("Unsafe filename: path separators, '..' and control characters are not allowed")
    return name


def validate_upload(filename, data: bytes, max_bytes: int) -> Upload:
    name = safe_filename(filename)
    ext = "." + name.rsplit(".", 1)[-1].lower() if "." in name else ""
    if ext not in ALLOWED:
        raise ValidationFailed("Only .csv and .json files are accepted")
    if len(data) == 0:
        raise ValidationFailed("The file is empty")
    if len(data) > max_bytes:
        raise TooLarge(f"The file is larger than the {max_bytes} byte limit")
    if bytes([0]) in data:
        raise ValidationFailed("The file contains binary data, not text")
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValidationFailed("The file is not valid UTF-8 text") from exc
    body = text.lstrip()
    if not body:
        raise ValidationFailed("The file contains no content")
    if ALLOWED[ext] == "JSON" and body[0] not in "[{":
        raise ValidationFailed("The file does not look like JSON (expected a list or object)")
    if ALLOWED[ext] == "CSV":
        if body[0] in "[{":
            raise ValidationFailed("The file looks like JSON but has a .csv extension")
        if "," not in body.splitlines()[0]:
            raise ValidationFailed("The CSV header line has no comma-separated columns")
    return Upload(filename=name, file_type=ALLOWED[ext], text=text, size=len(data))
