from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Callable, Dict, List, Optional, Tuple


class SessionType(Enum):
    """The kind of trading session a schedule entry represents.

    HALF_DAY is distinct from REGULAR so callers can, for instance, avoid
    routing late-day strategies through markets that close at lunchtime.
    """

    REGULAR = "regular"
    HALF_DAY = "half_day"


@dataclass(frozen=True)
class MarketSession:
    """A single contiguous open->close interval on a specific calendar date.

    All times are naive and interpreted in the market's local timezone. Keeping
    them naive avoids pulling in a tz library while still letting callers
    compare sessions on equal footing; the caller owns tz conversion.
    """

    date: str
    open_time: str
    close_time: str
    session_type: SessionType

    @property
    def is_half_day(self) -> bool:
        return self.session_type is SessionType.HALF_DAY


@dataclass(frozen=True)
class MarketSchedule:
    """Full per-date breakdown for one market, pre-computed for fast lookup."""

    market_code: str
    sessions: List[MarketSession]

    def session_for(self, date_str: str) -> Optional[MarketSession]:
        for s in self.sessions:
            if s.date == date_str:
                return s
        return None


@dataclass(frozen=True)
class _Spec:
    """Internal: the static rules for one market.

    A market is defined by its weekly open/close pattern plus an explicit set
    of overrides. The weekly pattern uses ISO weekday numbers (1=Mon ... 7=Sun)
    so that the weekend-shift case (e.g. TADAWUL, historically Sat-Wed) can be
    expressed directly without a separate weekend field.
    """

    market_code: str
    weekly: Dict[int, Tuple[str, str]]
    overrides: Dict[str, Tuple[str, str, SessionType]]


class TradingHoursCalendar:
    """Resolve open/close times for global exchanges.

    The constructor takes a clock function returning an ISO date string
    (YYYY-MM-DD). This is the single seam between the calendar and wall time;
    passing a fake clock in tests makes every assertion deterministic.

    Supported markets: NYSE/NASDAQ (XNYS), LSE (XLON), HKEX (XHKG), TADAWUL
    (XSAU). XSAU is included specifically because it historically traded
    Saturday-Wednesday, which is the "weekend shift" case the library exists
    to handle.
    """

    _DEFAULT_SPECS: Dict[str, _Spec] = {
        "XNYS": _Spec(
            market_code="XNYS",
            weekly={
                1: ("09:30", "16:00"),
                2: ("09:30", "16:00"),
                3: ("09:30", "16:00"),
                4: ("09:30", "16:00"),
                5: ("09:30", "16:00"),
            },
            overrides={},
        ),
        "XLON": _Spec(
            market_code="XLON",
            weekly={
                1: ("08:00", "16:30"),
                2: ("08:00", "16:30"),
                3: ("08:00", "16:30"),
                4: ("08:00", "16:30"),
                5: ("08:00", "16:30"),
            },
            overrides={},
        ),
        "XHKG": _Spec(
            market_code="XHKG",
            weekly={
                1: ("09:30", "16:00"),
                2: ("09:30", "16:00"),
                3: ("09:30", "16:00"),
                4: ("09:30", "16:00"),
                5: ("09:30", "16:00"),
            },
            overrides={},
        ),
        "XSAU": _Spec(
            market_code="XSAU",
            # Historical pattern: Saturday-Wednesday. Stated plainly because
            # this is the weekend-shift the library is built around.
            weekly={
                6: ("10:00", "15:00"),
                7: ("10:00", "15:00"),
                1: ("10:00", "15:00"),
                2: ("10:00", "15:00"),
                3: ("10:00", "15:00"),
            },
            overrides={},
        ),
    }

    def __init__(
        self,
        clock: Callable[[], str],
        specs: Optional[Dict[str, _Spec]] = None,
    ) -> None:
        self._clock = clock
        self._specs = dict(specs) if specs is not None else dict(self._DEFAULT_SPECS)

    @staticmethod
    def _iso_weekday(date_str: str) -> int:
        y, m, d = date_str.split("-")
        # date.isoweekday: Monday=1 ... Sunday=7. Plain integer arithmetic,
        # no datetime dependency on the clock, so this works on any input.
        import datetime
        return datetime.date(int(y), int(m), int(d)).isoweekday()

    def _resolve(self, market_code: str, date_str: str) -> Optional[MarketSession]:
        spec = self._specs.get(market_code)
        if spec is None:
            return None
        if date_str in spec.overrides:
            o, c, st = spec.overrides[date_str]
            return MarketSession(
                date=date_str, open_time=o, close_time=c, session_type=st
            )
        wd = self._iso_weekday(date_str)
        if wd in spec.weekly:
            o, c = spec.weekly[wd]
            return MarketSession(
                date=date_str,
                open_time=o,
                close_time=c,
                session_type=SessionType.REGULAR,
            )
        return None

    def session_for(self, market_code: str, date_str: str) -> Optional[MarketSession]:
        """Return the session for a market on a date, or None if closed."""
        return self._resolve(market_code, date_str)

    def schedule(self, market_code: str, dates: List[str]) -> MarketSchedule:
        """Build a MarketSchedule over an explicit list of date strings."""
        sessions: List[MarketSession] = []
        for d in dates:
            s = self._resolve(market_code, d)
            if s is not None:
                sessions.append(s)
        return MarketSchedule(market_code=market_code, sessions=sessions)

    def is_open(self, market_code: str) -> bool:
        """Whether a market is open right now according to the injected clock."""
        now = self._clock()
        date_part, time_part = now.split("T")
        session = self._resolve(market_code, date_part)
        if session is None:
            return False
        return session.open_time <= time_part < session.close_time
