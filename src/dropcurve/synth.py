"""Synthetic listening logs with known problems planted in them.

Real logs can't be shared, and a detector is only trustworthy if it finds
problems you put there on purpose. Every planted effect is listed in
`Truth`, and the tests check that the analysis finds each one.
"""

import random
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

from .events import Event


@dataclass
class Truth:
    series: str = "the-last-heir"
    episodes: int = 30
    duration: float = 480.0  # seconds per episode
    base_leave: float = 0.1  # chance a listener leaves somewhere inside an episode
    base_pull: float = 0.92  # chance a finisher starts the next episode
    cliffs: dict[int, tuple[float, float]] = field(default_factory=dict)  # ep -> (at, extra)
    weak_endings: dict[int, float] = field(default_factory=dict)  # ep -> pull instead
    drag: dict[int, float] = field(default_factory=dict)  # ep -> leave chance instead

    @classmethod
    def demo(cls) -> "Truth":
        """The planted problems used by `dropcurve synth` and the tests."""
        return cls(
            cliffs={6: (0.41, 0.12)},  # an ad break 41% into episode 6
            weak_endings={9: 0.45},  # episode 9 ends on a resolution, not a hook
            drag={14: 0.55},  # episode 14 is a slow one: people drift off all through it
        )


def _view(rng: random.Random, t: Truth, ep: int) -> float:
    """Furthest point (0..1) one listener reaches in episode ep."""
    at, extra = t.cliffs.get(ep, (None, 0.0))
    if at is not None and rng.random() < extra:
        return at + rng.uniform(0, 0.008)
    leave = t.drag.get(ep, t.base_leave)
    if rng.random() < leave:
        return rng.random()
    return 1.0


def generate(
    users: int = 2000,
    truth: Truth | None = None,
    seed: int = 7,
    start: datetime = datetime(2026, 1, 5, tzinfo=UTC),
    days: int = 28,
    ping: float = 120.0,
) -> list[Event]:
    t = truth or Truth()
    rng = random.Random(seed)
    events = []
    for i in range(users):
        user = f"u{i:06d}"
        now = start + timedelta(seconds=rng.uniform(0, days * 86400))
        for ep in range(1, t.episodes + 1):
            heard = _view(rng, t, ep)
            secs = heard * t.duration
            pos = 0.0
            while True:
                pos = min(pos + ping, secs)
                events.append(
                    Event(
                        user, t.series, ep, round(pos, 1), t.duration, now + timedelta(seconds=pos)
                    )
                )
                if pos >= secs:
                    break
            now += timedelta(seconds=secs)
            if heard < 0.9:
                break
            pull = t.weak_endings.get(ep, t.base_pull)
            if rng.random() >= pull:
                break
            # Most go straight on; some come back hours or days later.
            gap = rng.uniform(5, 120) if rng.random() < 0.7 else rng.uniform(3600, 3 * 86400)
            now += timedelta(seconds=gap)
    return events
