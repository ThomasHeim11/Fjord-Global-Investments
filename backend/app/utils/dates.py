"""Normalize the mixed date formats found in board_updates.json.

Observed formats: '2026-05-31' (ISO), '05/25/2026' (US month-first),
'15 May 2026' (day month year). Assumption: slash dates are US-style MM/DD/YYYY
— every slash date in the dataset is valid under that reading, and several
(e.g. 05/25/2026) are only valid month-first. Flagged for the interview.
"""
from datetime import datetime

_FORMATS = ["%Y-%m-%d", "%m/%d/%Y", "%d %B %Y", "%d %b %Y"]


def to_iso(raw: str) -> str | None:
    raw = (raw or "").strip()
    for fmt in _FORMATS:
        try:
            return datetime.strptime(raw, fmt).date().isoformat()
        except ValueError:
            continue
    return None
