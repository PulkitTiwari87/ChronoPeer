"""Timestamp normalisation.

Rule: a UTC value exists only when the timezone is KNOWN (explicit Z/offset) or ASSUMED (the
investigator supplied one at import). A timestamp with no timezone and no assumption stays UNKNOWN:
it is never converted with the computer's local timezone.
"""
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone


@dataclass(frozen=True)
class Normalized:
    utc: datetime | None  # naive UTC; None unless status is known/assumed
    status: str  # known | assumed | unknown | invalid | missing
    wall: datetime | None = None  # naive wall-clock value; used only to order unknown-timezone events


def parse_assumed_tz(value):
    """'UTC', 'Z', '+05:30', '-08:00' -> tzinfo. Blank/None/'unknown' -> None. Anything else is an error."""
    from . import ValidationFailed

    v = (value or "").strip()
    if v == "" or v.lower() == "unknown":
        return None
    if v.upper() in ("UTC", "Z"):
        return timezone.utc
    sign = v[0]
    digits = v[1:].replace(":", "")
    if sign in "+-" and len(digits) == 4 and digits.isdigit():
        hours, minutes = int(digits[:2]), int(digits[2:])
        if hours <= 14 and minutes < 60:
            delta = timedelta(hours=hours, minutes=minutes)
            return timezone(delta if sign == "+" else -delta)
    raise ValidationFailed("assume_timezone must be UTC or an offset such as +05:30")


def normalize(raw, assume_tz=None) -> Normalized:
    text = (raw or "").strip()
    if not text:
        return Normalized(None, "missing")
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return Normalized(None, "invalid")
    if parsed.tzinfo is not None:
        return Normalized(parsed.astimezone(timezone.utc).replace(tzinfo=None), "known")
    if assume_tz is not None:
        return Normalized(parsed.replace(tzinfo=assume_tz).astimezone(timezone.utc).replace(tzinfo=None), "assumed")
    return Normalized(None, "unknown", wall=parsed)
