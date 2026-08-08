from __future__ import annotations

import re
import unicodedata
from datetime import datetime, timedelta, timezone


GENRES = {
    "reggae", "jazz", "rock", "rap", "hip hop", "hip-hop", "classique",
    "electro", "électro", "techno", "salsa", "metal", "blues", "soul",
    "funk", "gospel", "punk", "folk", "afro", "rnb", "r&b",
}

FREE_TERMS = {
    "gratuit", "gratuite", "gratuits", "gratuites", "entrée libre",
    "entree libre", "accès libre", "acces libre", "free", "0 €", "0€",
}

PAST_TERMS = {
    "passé", "passe", "passés", "passes", "hier", "semaine dernière",
    "semaine derniere", "mois dernier", "année dernière", "annee derniere",
    "a eu lieu", "ont eu lieu", "ancien", "ancienne",
}

EVENT_TYPES = {
    "concert": {"concert", "live", "musique", "musical"},
    "exposition": {"exposition", "expo", "galerie"},
    "atelier": {"atelier", "workshop"},
    "conférence": {"conference", "conférence", "colloque", "talk"},
    "spectacle": {"spectacle", "theatre", "théâtre", "scene", "scène"},
}


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFKD", str(text or ""))
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = text.casefold()
    text = re.sub(r"[^a-z0-9&€-]+", " ", text)
    return " ".join(text.split())


def _contains_term(text: str, term: str) -> bool:
    """Recherche un terme sur des frontières de mots, pas comme sous-chaîne."""
    haystack = f" {normalize(text)} "
    needle = normalize(term)
    return bool(needle) and f" {needle} " in haystack


def requested_genres(question: str) -> set[str]:
    return {normalize(g) for g in GENRES if _contains_term(question, g)}


def _field(document_text: str, label: str) -> str:
    """Extrait une ligne structurée produite par indexer.event_text()."""
    pattern = rf"(?im)^{re.escape(label)}\s*:\s*(.*)$"
    match = re.search(pattern, document_text or "")
    return match.group(1).strip() if match else ""


def passes_genre_guard(question: str, document_text: str) -> bool:
    """
    Un genre demandé doit être explicitement présent dans le TITRE ou les
    MOTS-CLÉS. On n'utilise pas la description libre pour éviter qu'un texte
    mentionnant 'reggae' par comparaison soit présenté comme concert reggae.
    """
    genres = requested_genres(question)
    if not genres:
        return True

    trusted = " ".join([
        _field(document_text, "Titre"),
        _field(document_text, "Mots-clés"),
    ])
    return any(_contains_term(trusted, genre) for genre in genres)


def asks_for_free(question: str) -> bool:
    return any(_contains_term(question, term) for term in FREE_TERMS)


def passes_free_guard(question: str, document_text: str) -> bool:
    if not asks_for_free(question):
        return True

    # La gratuité peut être indiquée dans le titre, les mots-clés ou la
    # description. En revanche, absence d'information != gratuit.
    return any(_contains_term(document_text, term) for term in FREE_TERMS)


def requested_event_types(question: str) -> set[str]:
    found = set()
    for event_type, aliases in EVENT_TYPES.items():
        if any(_contains_term(question, alias) for alias in aliases):
            found.add(event_type)
    return found


def passes_event_type_guard(question: str, document_text: str) -> bool:
    requested = requested_event_types(question)
    if not requested:
        return True

    # Pour le type d'événement, titre + mots-clés + description sont admis.
    # Il faut toutefois une preuve lexicale explicite.
    for event_type in requested:
        aliases = EVENT_TYPES[event_type]
        if any(_contains_term(document_text, alias) for alias in aliases):
            return True
    return False


def explicitly_requests_past(question: str) -> bool:
    return any(_contains_term(question, term) for term in PAST_TERMS)


def _parse_iso(value: str):
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


MONTHS = {
    "janvier": 1, "fevrier": 2, "février": 2, "mars": 3, "avril": 4,
    "mai": 5, "juin": 6, "juillet": 7, "aout": 8, "août": 8,
    "septembre": 9, "octobre": 10, "novembre": 11, "decembre": 12,
    "décembre": 12,
}


def requested_period(question: str, now: datetime | None = None):
    """
    Retourne la période demandée.

    Règle importante : sans demande explicite de passé, une requête sans date
    ne peut jamais retourner un événement déjà terminé.
    """
    now = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    q = question.casefold()

    if "aujourd" in q:
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        return start, start + timedelta(days=1)

    if "demain" in q:
        start = (now + timedelta(days=1)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
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
            if year_match:
                year = int(year_match.group(1))
            else:
                # Sans année, on vise la prochaine occurrence du mois.
                year = now.year
                month_end = (
                    datetime(year + 1, 1, 1, tzinfo=timezone.utc)
                    if month == 12
                    else datetime(year, month + 1, 1, tzinfo=timezone.utc)
                )
                if month_end <= now and not explicitly_requests_past(question):
                    year += 1

            start = datetime(year, month, 1, tzinfo=timezone.utc)
            end = (
                datetime(year + 1, 1, 1, tzinfo=timezone.utc)
                if month == 12
                else datetime(year, month + 1, 1, tzinfo=timezone.utc)
            )
            return start, end

    if explicitly_requests_past(question):
        return None

    # Par défaut : maintenant -> futur lointain. Cela élimine les événements
    # terminés sans empêcher les événements en cours.
    return now, datetime(2100, 1, 1, tzinfo=timezone.utc)


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
