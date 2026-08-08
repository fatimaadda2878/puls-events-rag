from __future__ import annotations

import re
import unicodedata
from datetime import datetime, timedelta, timezone


GENRES = {
    "reggae", "jazz", "rock", "rap", "hip hop", "hip-hop", "classique",
    "electro", "électro", "techno", "salsa", "metal", "blues", "soul",
    "funk", "gospel", "punk", "folk", "afro", "rnb", "r&b",
}


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFKD", str(text or ""))
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = text.casefold()
    text = re.sub(r"[^a-z0-9&-]+", " ", text)
    return " ".join(text.split())


def requested_genres(question: str) -> set[str]:
    q = normalize(question)
    found = set()
    for genre in GENRES:
        if normalize(genre) in q:
            found.add(normalize(genre))
    return found


def passes_genre_guard(question: str, document_text: str) -> bool:
    genres = requested_genres(question)
    if not genres:
        return True
    text = normalize(document_text)
    return any(genre in text for genre in genres)


def _parse_iso(value: str):
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


MONTHS = {
    "janvier": 1, "fevrier": 2, "février": 2, "mars": 3, "avril": 4,
    "mai": 5, "juin": 6, "juillet": 7, "aout": 8, "août": 8,
    "septembre": 9, "octobre": 10, "novembre": 11, "decembre": 12,
    "décembre": 12,
}


def requested_period(question: str, now: datetime | None = None):
    """Parse quelques expressions temporelles utiles au POC."""
    now = now or datetime.now(timezone.utc)
    q = question.casefold()

    if "aujourd" in q:
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        return start, start + timedelta(days=1)

    if "demain" in q:
        start = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        return start, start + timedelta(days=1)

    if "cette semaine" in q:
        start = (now - timedelta(days=now.weekday())).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        return start, start + timedelta(days=7)

    if "ce week-end" in q or "ce weekend" in q:
        days_to_sat = (5 - now.weekday()) % 7
        start = (now + timedelta(days=days_to_sat)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        return start, start + timedelta(days=2)

    for label, month in MONTHS.items():
        if label in q:
            year_match = re.search(r"\b(20\d{2})\b", q)
            year = int(year_match.group(1)) if year_match else now.year
            start = datetime(year, month, 1, tzinfo=timezone.utc)
            if month == 12:
                end = datetime(year + 1, 1, 1, tzinfo=timezone.utc)
            else:
                end = datetime(year, month + 1, 1, tzinfo=timezone.utc)
            return start, end

    return None


def overlaps_period(metadata: dict, period) -> bool:
    if period is None:
        return True

    wanted_start, wanted_end = period
    event_start = _parse_iso(metadata.get("start", ""))
    event_end = _parse_iso(metadata.get("end", "")) or event_start

    if event_start is None and event_end is None:
        return False
    event_start = event_start or event_end
    event_end = event_end or event_start

    return event_start < wanted_end and event_end >= wanted_start
