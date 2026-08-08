from __future__ import annotations

import csv
import io
import json
from datetime import datetime, timedelta, timezone
from typing import Any, Iterator

import requests

from .config import (
    OPENAGENDA_API_URL,
    OPENAGENDA_CITY,
    OPENAGENDA_MAX_EVENTS,
    OPENAGENDA_PAGE_SIZE,
)

# Documentation OpenDataSoft : offset + limit doit rester < 10 000.
RECORDS_SAFE_WINDOW = 9900


def _pick(record: dict[str, Any], *names: str, default=""):
    for name in names:
        value = record.get(name)
        if value not in (None, "", []):
            return value
    return default


def _parse_date(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(str(value).strip().replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _keywords(value: Any) -> list[str]:
    if value in (None, ""):
        return []
    if isinstance(value, list):
        return [str(x).strip() for x in value if str(x).strip()]
    if isinstance(value, tuple):
        return [str(x).strip() for x in value if str(x).strip()]

    text = str(value).strip()
    # Certains exports peuvent sérialiser une liste JSON.
    if text.startswith("[") and text.endswith("]"):
        try:
            parsed = json.loads(text)
            if isinstance(parsed, list):
                return [str(x).strip() for x in parsed if str(x).strip()]
        except json.JSONDecodeError:
            pass

    # CSV OpenDataSoft : les champs multivalués sont généralement séparés par ",".
    return [x.strip() for x in text.replace(";", ",").split(",") if x.strip()]


def normalize_event(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(_pick(record, "uid", "id", "slug", default="")),
        "title": str(
            _pick(record, "title_fr", "title", "name", default="Sans titre")
        ).strip(),
        "description": str(
            _pick(
                record,
                "description_fr",
                "longdescription_fr",
                "description",
                default="",
            )
        ).strip(),
        "keywords": _keywords(_pick(record, "keywords_fr", "keywords", default=[])),
        "city": str(_pick(record, "location_city", "city", default="")).strip(),
        "address": str(_pick(record, "location_address", "address", default="")).strip(),
        "start": str(
            _pick(
                record,
                "firstdate_begin",
                "daterange_start",
                "date_start",
                default="",
            )
        ).strip(),
        "end": str(
            _pick(
                record,
                "lastdate_end",
                "daterange_end",
                "date_end",
                default="",
            )
        ).strip(),
        "url": str(
            _pick(record, "canonicalurl", "canonical_url", "url", default="")
        ).strip(),
    }


def _is_recent(event: dict[str, Any], cutoff: datetime) -> bool:
    # Pour un événement qui dure plusieurs jours, on considère sa date de fin.
    end = _parse_date(event.get("end") or event.get("start"))
    # On conserve les enregistrements sans date plutôt que de les perdre silencieusement.
    return end is None or end >= cutoff


def _dedupe_key(event: dict[str, Any]):
    return event["id"] or (
        event["title"].casefold(),
        event["start"],
        event["address"].casefold(),
    )


def _where(city: str, cutoff: datetime, include_date: bool = True) -> str:
    city_escaped = city.replace('"', '\\"')
    base = f'location_city="{city_escaped}"'
    if not include_date:
        return base

    # Filtre serveur pour limiter l'export à l'historique d'un an + futur.
    # Si le portail refuse ce filtre (schéma différent), le code retente
    # automatiquement avec le filtre ville uniquement.
    date_literal = cutoff.date().isoformat()
    return (
        f"{base} AND "
        f"(lastdate_end >= date'{date_literal}' OR firstdate_begin >= date'{date_literal}')"
    )


def _request_json(session, url: str, *, params: dict, timeout: int = 30):
    response = session.get(url, params=params, timeout=timeout)
    response.raise_for_status()
    return response.json()


def _first_page(session, city: str, cutoff: datetime) -> tuple[dict, str]:
    candidates = [_where(city, cutoff, True), _where(city, cutoff, False)]
    last_error: Exception | None = None

    for where in candidates:
        try:
            payload = _request_json(
                session,
                OPENAGENDA_API_URL,
                params={
                    "limit": OPENAGENDA_PAGE_SIZE,
                    "offset": 0,
                    "where": where,
                },
            )
            return payload, where
        except requests.HTTPError as exc:
            last_error = exc
            status = getattr(exc.response, "status_code", None)
            # Un 400 peut venir du filtre de date. Les autres codes remontent.
            if status != 400:
                raise

    raise RuntimeError(
        f"OpenAgenda refuse les filtres de récupération : {last_error}"
    ) from last_error


def _iter_records_pages(
    session,
    *,
    where: str,
    first_payload: dict[str, Any],
) -> Iterator[dict[str, Any]]:
    payload = first_payload
    offset = 0

    while True:
        rows = list(payload.get("results", []) or [])
        total = int(payload.get("total_count") or 0)

        if not rows:
            return

        yield from rows
        offset += len(rows)

        if total and offset >= total:
            return
        if len(rows) < OPENAGENDA_PAGE_SIZE:
            return

        # Ne jamais reproduire l'erreur offset=10000 rencontrée sur Render.
        if offset + OPENAGENDA_PAGE_SIZE >= 10000:
            raise RuntimeError(
                "Pagination OpenDataSoft profonde détectée. "
                "Le code doit utiliser l'endpoint /exports."
            )

        payload = _request_json(
            session,
            OPENAGENDA_API_URL,
            params={
                "limit": OPENAGENDA_PAGE_SIZE,
                "offset": offset,
                "where": where,
            },
        )


def _export_csv_url() -> str:
    base = OPENAGENDA_API_URL.rstrip("/")
    if base.endswith("/records"):
        return base[:-len("/records")] + "/exports/csv"
    if "/exports/" in base:
        return base.rsplit("/exports/", 1)[0] + "/exports/csv"
    return base + "/exports/csv"


def _iter_export_csv(session, *, where: str) -> Iterator[dict[str, Any]]:
    """
    Lecture streaming de l'export CSV OpenDataSoft.

    Contrairement à response.json(), aucun export complet n'est chargé en RAM.
    C'est le chemin utilisé quand le résultat dépasse la fenêtre de 10 000.
    """
    response = session.get(
        _export_csv_url(),
        params={
            "where": where,
            "limit": -1,
            "use_labels": "false",
            "delimiter": ";",
            "with_bom": "false",
        },
        timeout=(15, 300),
        stream=True,
    )
    response.raise_for_status()

    # Décompression HTTP éventuelle.
    if hasattr(response.raw, "decode_content"):
        response.raw.decode_content = True

    text_stream = io.TextIOWrapper(
        response.raw,
        encoding="utf-8-sig",
        newline="",
    )
    reader = csv.DictReader(text_stream, delimiter=";")
    for row in reader:
        if row:
            yield dict(row)


def iter_all_events(
    session=requests,
    city: str = OPENAGENDA_CITY,
) -> Iterator[dict[str, Any]]:
    """
    Récupère tous les événements du périmètre :
    - pagination /records si le total tient dans la fenêtre OpenDataSoft ;
    - export CSV illimité en streaming au-delà ;
    - filtre d'un an d'historique + événements futurs ;
    - déduplication.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=365)
    first_payload, where = _first_page(session, city, cutoff)
    total = int(first_payload.get("total_count") or 0)

    if total > RECORDS_SAFE_WINDOW:
        raw_iter = _iter_export_csv(session, where=where)
    else:
        raw_iter = _iter_records_pages(
            session,
            where=where,
            first_payload=first_payload,
        )

    seen = set()
    emitted = 0

    for raw in raw_iter:
        event = normalize_event(raw)

        # Double sécurité : même si le filtre date serveur est tombé en fallback,
        # le périmètre temporel est garanti localement.
        if not _is_recent(event, cutoff):
            continue

        key = _dedupe_key(event)
        if key in seen:
            continue

        seen.add(key)
        yield event
        emitted += 1

        if OPENAGENDA_MAX_EVENTS and emitted >= OPENAGENDA_MAX_EVENTS:
            return


def fetch_all_events(
    session=requests,
    city: str = OPENAGENDA_CITY,
) -> list[dict[str, Any]]:
    """API pratique pour tests/usage local ; l'indexeur utilise l'itérateur streaming."""
    return list(iter_all_events(session=session, city=city))
