from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import Any

import requests

from .config import (
    OPENAGENDA_API_URL,
    OPENAGENDA_CITY,
    OPENAGENDA_PAGE_SIZE,
    OPENAGENDA_MAX_EVENTS,
)

# Sur le endpoint /records, OpenDataSoft limite la pagination profonde.
# Quand le nombre de résultats dépasse cette fenêtre, on bascule sur /exports/json,
# qui n'a pas cette limitation.
RECORDS_SAFE_WINDOW = 9900


def _pick(record: dict, *names: str, default=""):
    for name in names:
        value = record.get(name)
        if value not in (None, "", []):
            return value
    return default


def _date(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None


def normalize_event(record: dict[str, Any]) -> dict[str, Any]:
    """Normalise un enregistrement OpenAgenda vers le format interne du projet."""
    return {
        "id": str(_pick(record, "uid", "id", "slug", default="")),
        "title": str(
            _pick(record, "title_fr", "title", "name", default="Sans titre")
        ),
        "description": str(
            _pick(
                record,
                "description_fr",
                "longdescription_fr",
                "description",
                default="",
            )
        ),
        "keywords": _pick(record, "keywords_fr", "keywords", default=[]),
        "city": str(_pick(record, "location_city", "city", default="")),
        "address": str(_pick(record, "location_address", "address", default="")),
        "start": str(
            _pick(
                record,
                "firstdate_begin",
                "daterange_start",
                "date_start",
                default="",
            )
        ),
        "end": str(
            _pick(
                record,
                "lastdate_end",
                "daterange_end",
                "date_end",
                default="",
            )
        ),
        "url": str(
            _pick(record, "canonicalurl", "canonical_url", "url", default="")
        ),
    }


def _is_recent(event: dict[str, Any], cutoff: datetime) -> bool:
    """Conserve les événements terminés depuis moins d'un an ou futurs."""
    end = _date(event["end"] or event["start"])

    # Si aucune date n'est exploitable, on conserve l'événement plutôt
    # que de le supprimer silencieusement.
    if end is None:
        return True

    if end.tzinfo is None:
        end = end.replace(tzinfo=timezone.utc)

    return end >= cutoff


def _deduplicate_and_filter(
    rows: list[dict[str, Any]],
    cutoff: datetime,
    max_events: int = 0,
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    seen = set()

    for raw in rows:
        event = normalize_event(raw)

        if not _is_recent(event, cutoff):
            continue

        key = event["id"] or (
            event["title"],
            event["start"],
            event["address"],
        )

        if key in seen:
            continue

        seen.add(key)
        out.append(event)

        if max_events and len(out) >= max_events:
            break

    return out


def _export_url(records_url: str) -> str:
    """Construit l'URL /exports/json à partir de l'URL /records."""
    base = records_url.rstrip("/")

    if base.endswith("/records"):
        return base[: -len("/records")] + "/exports/json"

    # Permet aussi de fournir directement une URL de dataset via variable d'env.
    return base + "/exports/json"


def _fetch_via_export(
    session,
    city: str,
    cutoff: datetime,
) -> list[dict[str, Any]]:
    """
    Récupère tous les résultats avec l'endpoint d'export.

    L'endpoint /exports n'est pas soumis à la limite de pagination profonde
    du endpoint /records.
    """
    url = _export_url(OPENAGENDA_API_URL)
    params = {"where": f'location_city="{city}"'}

    response = session.get(url, params=params, timeout=120)
    response.raise_for_status()
    payload = response.json()

    # /exports/json renvoie normalement une liste JSON.
    # On tolère aussi {"results": [...]} pour rester robuste.
    if isinstance(payload, list):
        rows = payload
    elif isinstance(payload, dict):
        rows = payload.get("results", [])
    else:
        raise ValueError(
            "Format inattendu reçu depuis l'export OpenDataSoft."
        )

    return _deduplicate_and_filter(
        rows,
        cutoff=cutoff,
        max_events=OPENAGENDA_MAX_EVENTS,
    )


def fetch_all_events(
    session=requests,
    city: str = OPENAGENDA_CITY,
) -> list[dict[str, Any]]:
    """
    Récupère les événements OpenAgenda pour une ville.

    Stratégie :
    1. Première page via /records afin de lire total_count.
    2. Si le volume dépasse la fenêtre sûre de pagination,
       bascule immédiatement sur /exports/json.
    3. Sinon, pagination classique avec offset.
    4. Déduplication + filtre de récence (< 1 an pour les événements passés).

    OPENAGENDA_MAX_EVENTS = 0 signifie "aucune limite artificielle".
    """
    page_size = max(1, min(int(OPENAGENDA_PAGE_SIZE), 100))
    cutoff = datetime.now(timezone.utc) - timedelta(days=365)

    offset = 0
    out: list[dict[str, Any]] = []
    seen = set()

    while True:
        params = {
            "limit": page_size,
            "offset": offset,
            "where": f'location_city="{city}"',
        }

        response = session.get(
            OPENAGENDA_API_URL,
            params=params,
            timeout=30,
        )
        response.raise_for_status()
        payload = response.json()

        rows = payload.get("results", [])
        total = payload.get("total_count")

        # Si l'ensemble des résultats dépasse la fenêtre permise par /records,
        # on utilise l'export complet plutôt que d'atteindre un offset interdit.
        if (
            offset == 0
            and total is not None
            and int(total) > RECORDS_SAFE_WINDOW
            and (
                OPENAGENDA_MAX_EVENTS == 0
                or OPENAGENDA_MAX_EVENTS > RECORDS_SAFE_WINDOW
            )
        ):
            return _fetch_via_export(
                session=session,
                city=city,
                cutoff=cutoff,
            )

        if not rows:
            break

        for raw in rows:
            event = normalize_event(raw)

            if not _is_recent(event, cutoff):
                continue

            key = event["id"] or (
                event["title"],
                event["start"],
                event["address"],
            )

            if key in seen:
                continue

            seen.add(key)
            out.append(event)

            if (
                OPENAGENDA_MAX_EVENTS
                and len(out) >= OPENAGENDA_MAX_EVENTS
            ):
                return out

        offset += len(rows)

        if total is not None and offset >= int(total):
            break

        if len(rows) < page_size:
            break

        # Sécurité supplémentaire : ne jamais demander un offset profond
        # susceptible d'être refusé par OpenDataSoft.
        if offset + page_size > RECORDS_SAFE_WINDOW:
            return _fetch_via_export(
                session=session,
                city=city,
                cutoff=cutoff,
            )

    return out
