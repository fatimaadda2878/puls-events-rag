from __future__ import annotations
from datetime import datetime, timezone, timedelta
from typing import Any
import requests
from .config import OPENAGENDA_API_URL, OPENAGENDA_CITY, OPENAGENDA_PAGE_SIZE, OPENAGENDA_MAX_EVENTS

def _pick(r: dict, *names, default=""):
    for n in names:
        v=r.get(n)
        if v not in (None, "", []): return v
    return default

def _date(v):
    if not v: return None
    try: return datetime.fromisoformat(str(v).replace("Z", "+00:00"))
    except ValueError: return None

def normalize_event(r: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(_pick(r,"uid","id","slug", default="")),
        "title": str(_pick(r,"title_fr","title","name", default="Sans titre")),
        "description": str(_pick(r,"description_fr","longdescription_fr","description", default="")),
        "keywords": _pick(r,"keywords_fr","keywords", default=[]),
        "city": str(_pick(r,"location_city","city", default="")),
        "address": str(_pick(r,"location_address","address", default="")),
        "start": str(_pick(r,"firstdate_begin","daterange_start","date_start", default="")),
        "end": str(_pick(r,"lastdate_end","daterange_end","date_end", default="")),
        "url": str(_pick(r,"canonicalurl","canonical_url","url", default="")),
    }

def fetch_all_events(session=requests, city: str=OPENAGENDA_CITY) -> list[dict[str, Any]]:
    offset=0; out=[]; seen=set()
    cutoff=datetime.now(timezone.utc)-timedelta(days=365)
    while True:
        params={"limit":OPENAGENDA_PAGE_SIZE,"offset":offset,"where":f'location_city="{city}"'}
        resp=session.get(OPENAGENDA_API_URL, params=params, timeout=30)
        resp.raise_for_status(); payload=resp.json(); rows=payload.get("results", [])
        if not rows: break
        for raw in rows:
            ev=normalize_event(raw)
            end=_date(ev["end"] or ev["start"])
            if end and end.tzinfo is None: end=end.replace(tzinfo=timezone.utc)
            if end and end < cutoff: continue
            key=ev["id"] or (ev["title"],ev["start"],ev["address"])
            if key in seen: continue
            seen.add(key); out.append(ev)
            if OPENAGENDA_MAX_EVENTS and len(out)>=OPENAGENDA_MAX_EVENTS: return out
        offset += len(rows)
        total=payload.get("total_count")
        if total is not None and offset >= int(total): break
        if len(rows) < OPENAGENDA_PAGE_SIZE: break
    return out
