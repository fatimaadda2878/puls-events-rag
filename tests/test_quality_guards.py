from datetime import datetime, timezone

from app.filters import (
    passes_free_guard,
    passes_genre_guard,
    requested_period,
    overlaps_period,
)


REGGAE = """Titre: Roots Reggae Dub célébration
Description: Une soirée musicale.
Mots-clés: reggae, dub, concert
Ville: Paris
Début: 2026-09-01T18:00:00+00:00
Fin: 2026-09-01T22:00:00+00:00"""

NOT_REGGAE = """Titre: Only French Show
Description: Une soirée qui évoque plusieurs styles dont le reggae dans sa présentation.
Mots-clés: humour, français
Ville: Paris
Début: 2026-09-01T18:00:00+00:00
Fin: 2026-09-01T22:00:00+00:00"""

FREE = """Titre: Concert d'été
Description: Concert gratuit, entrée libre.
Mots-clés: musique, concert
Ville: Paris"""

PAID_OR_UNKNOWN = """Titre: Concert d'été
Description: Billetterie sur place.
Mots-clés: musique, concert
Ville: Paris"""


def test_reggae_guard_uses_title_or_keywords_only():
    assert passes_genre_guard("concert reggae à Paris", REGGAE)
    assert not passes_genre_guard("concert reggae à Paris", NOT_REGGAE)


def test_free_is_strict():
    assert passes_free_guard("concert gratuit à Paris", FREE)
    assert not passes_free_guard("concert gratuit à Paris", PAID_OR_UNKNOWN)


def test_no_date_defaults_to_future():
    now = datetime(2026, 8, 8, 15, 0, tzinfo=timezone.utc)
    period = requested_period("Y a-t-il des concerts de reggae à Paris ?", now=now)
    assert not overlaps_period(
        {"start": "2025-10-03T18:00:00+00:00", "end": "2025-10-03T21:30:00+00:00"},
        period,
    )
    assert overlaps_period(
        {"start": "2026-09-03T18:00:00+00:00", "end": "2026-09-03T21:30:00+00:00"},
        period,
    )


def test_month_without_year_uses_next_occurrence_when_month_is_over():
    now = datetime(2026, 8, 8, 15, 0, tzinfo=timezone.utc)
    start, end = requested_period("concerts gratuits en juillet", now=now)
    assert start.year == 2027 and start.month == 7
    assert end.year == 2027 and end.month == 8
