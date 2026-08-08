from datetime import datetime, timezone

from app.filters import (
    overlaps_period,
    passes_genre_guard,
    requested_period,
)


def test_reggae_guard_rejects_jazz():
    assert not passes_genre_guard(
        "Y a-t-il des concerts de reggae à Paris ?",
        "Titre: Soirée jazz\nDescription: concert de jazz",
    )


def test_reggae_guard_accepts_reggae():
    assert passes_genre_guard(
        "Y a-t-il des concerts de reggae à Paris ?",
        "Titre: Reggae night\nDescription: concert live",
    )


def test_this_week_period():
    now = datetime(2026, 8, 8, 12, tzinfo=timezone.utc)
    period = requested_period("Que faire cette semaine ?", now=now)
    assert period is not None


def test_period_overlap():
    period = (
        datetime(2026, 8, 3, tzinfo=timezone.utc),
        datetime(2026, 8, 10, tzinfo=timezone.utc),
    )
    assert overlaps_period(
        {"start": "2026-08-08T10:00:00+00:00", "end": "2026-08-08T12:00:00+00:00"},
        period,
    )
