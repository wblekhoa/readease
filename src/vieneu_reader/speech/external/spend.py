"""What this session has spent, counted as it happens.

Deliberately small and deliberately in memory: it answers "what have I run
up since I opened the app", which is the question a person asks before they
carry on. Nothing is written to disk, so nothing accumulates a record of what
somebody has been reading.
"""

from __future__ import annotations

from dataclasses import dataclass
from threading import Lock


@dataclass(frozen=True, slots=True)
class Spend:
    chars: int
    usd: float
    #: Stops further paid synthesis once reached. None = no ceiling.
    limit_usd: float | None = None

    @property
    def exhausted(self) -> bool:
        return self.limit_usd is not None and self.usd >= self.limit_usd


class SpendMeter:
    """Adds up characters and money, and says when to stop."""

    def __init__(self, limit_usd: float | None = None):
        self._lock = Lock()
        self._chars = 0
        self._usd = 0.0
        self._limit = limit_usd

    def set_limit(self, limit_usd: float | None) -> None:
        with self._lock:
            self._limit = limit_usd

    def add(self, chars: int, usd: float) -> Spend:
        with self._lock:
            self._chars += chars
            # Money is added at full precision and rounded only when read:
            # rounding each sentence would drift by a cent over a chapter.
            self._usd += usd
            return self._snapshot()

    def snapshot(self) -> Spend:
        with self._lock:
            return self._snapshot()

    def _snapshot(self) -> Spend:
        return Spend(chars=self._chars, usd=round(self._usd, 4), limit_usd=self._limit)

    def would_exceed(self, usd: float) -> bool:
        """True when spending this much more would pass the ceiling.

        Asked BEFORE a request goes out, so the limit is a limit rather than
        a thing noticed afterwards.
        """

        with self._lock:
            if self._limit is None:
                return False
            return self._usd + usd > self._limit
