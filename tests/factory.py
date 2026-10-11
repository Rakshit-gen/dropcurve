from datetime import UTC, datetime, timedelta

from dropcurve.events import Event

T0 = datetime(2026, 1, 5, 9, 0, tzinfo=UTC)


def ev(user, episode, position, minutes=0.0, series="s1", duration=600.0):
    return Event(user, series, episode, position, duration, T0 + timedelta(minutes=minutes))
