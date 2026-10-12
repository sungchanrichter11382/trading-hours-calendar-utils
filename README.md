# trading-hours-calendar-utils

Determines market open/close times for global stock exchanges, handling weekend shifts and half-day sessions.

## Usage

```python
from trading_hours_calendar_utils import TradingHoursCalendar

cal = TradingHoursCalendar(clock=lambda: "2024-01-15T12:00")

# Session for a specific market on a specific date (None if closed).
session = cal.session_for("XNYS", "2024-01-15")
# MarketSession(date="2024-01-15", open_time="09:30", close_time="16:00", ...)

# Is the market open right now, according to the injected clock?
cal.is_open("XNYS")   # True

# Build a schedule across an explicit list of dates.
sched = cal.schedule("XNYS", ["2024-01-13", "2024-01-15"])
# MarketSchedule(market_code="XNYS", sessions=[...])
```

Exported names: `TradingHoursCalendar`, `MarketSession`, `MarketSchedule`, `SessionType`.

## Why this exists

Most calendar libraries model weekends as a fixed Saturday-Sunday block. That breaks for markets whose trading week historically starts on Saturday (e.g. TADAWUL/XSAU). This library models each market as a weekday-to-hours map using ISO weekday numbers (1=Mon ... 7=Sun), so a Saturday-start week is just a different set of keys, not a special case.

The trade-off: there is no built-in holiday calendar. Public holidays are surfaced through explicit per-date overrides passed at construction time, not computed from a rules engine. This keeps the dependency surface at zero (standard library only) and makes every result deterministic and auditable.

## Awkward edges

- Times are naive `HH:MM` strings in the market's local timezone. If you need UTC conversion, own it on the caller side — this library deliberately does not pull in a tz database.
- `is_open` treats the close time as not open (half-open interval: `open <= now < close`).
- The clock function must return `YYYY-MM-DDTHH:MM`; `is_open` parses on the `T` separator.
- Half-day sessions carry `session_type=SessionType.HALF_DAY` and their `close_time` reflects the early close, so afternoon checks via `is_open` return False automatically.
