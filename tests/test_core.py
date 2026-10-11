import unittest

from trading_hours_calendar_utils import (
    TradingHoursCalendar,
    MarketSession,
    MarketSchedule,
    SessionType,
)


class TestCore(unittest.TestCase):
    def test_xnys_monday_regular(self):
        cal = TradingHoursCalendar(clock=lambda: "2024-01-15T10:00")
        s = cal.session_for("XNYS", "2024-01-15")
        self.assertIsNotNone(s)
        assert s is not None
        self.assertEqual(s.open_time, "09:30")
        self.assertEqual(s.close_time, "16:00")
        self.assertIs(s.session_type, SessionType.REGULAR)
        self.assertFalse(s.is_half_day)

    def test_xnys_saturday_closed(self):
        cal = TradingHoursCalendar(clock=lambda: "2024-01-13T10:00")
        self.assertIsNone(cal.session_for("XNYS", "2024-01-13"))

    def test_xnys_sunday_closed(self):
        cal = TradingHoursCalendar(clock=lambda: "2024-01-14T10:00")
        self.assertIsNone(cal.session_for("XNYS", "2024-01-14"))

    def test_xlon_weekly(self):
        cal = TradingHoursCalendar(clock=lambda: "2024-01-16T10:00")
        s = cal.session_for("XLON", "2024-01-16")
        self.assertIsNotNone(s)
        assert s is not None
        self.assertEqual(s.open_time, "08:00")
        self.assertEqual(s.close_time, "16:30")

    def test_xhkg_weekly(self):
        cal = TradingHoursCalendar(clock=lambda: "2024-01-17T10:00")
        s = cal.session_for("XHKG", "2024-01-17")
        self.assertIsNotNone(s)
        assert s is not None
        self.assertEqual(s.open_time, "09:30")
        self.assertEqual(s.close_time, "16:00")

    def test_xsau_saturday_open(self):
        # Saturday is a trading day for XSAU; this is the weekend-shift case.
        cal = TradingHoursCalendar(clock=lambda: "2024-01-13T10:00")
        s = cal.session_for("XSAU", "2024-01-13")
        self.assertIsNotNone(s)
        assert s is not None
        self.assertEqual(s.open_time, "10:00")
        self.assertEqual(s.close_time, "15:00")

    def test_xsau_friday_closed(self):
        cal = TradingHoursCalendar(clock=lambda: "2024-01-12T10:00")
        self.assertIsNone(cal.session_for("XSAU", "2024-01-12"))

    def test_unknown_market_returns_none(self):
        cal = TradingHoursCalendar(clock=lambda: "2024-01-15T10:00")
        self.assertIsNone(cal.session_for("XXXX", "2024-01-15"))

    def test_override_half_day(self):
        from trading_hours_calendar_utils.core import _Spec, SessionType
        spec = _Spec(
            market_code="TEST",
            weekly={1: ("09:30", "16:00")},
            overrides={"2024-01-15": ("09:30", "13:00", SessionType.HALF_DAY)},
        )
        cal = TradingHoursCalendar(
            clock=lambda: "2024-01-15T10:00", specs={"TEST": spec}
        )
        s = cal.session_for("TEST", "2024-01-15")
        self.assertIsNotNone(s)
        assert s is not None
        self.assertEqual(s.close_time, "13:00")
        self.assertIs(s.session_type, SessionType.HALF_DAY)
        self.assertTrue(s.is_half_day)

    def test_override_takes_precedence_over_weekly(self):
        from trading_hours_calendar_utils.core import _Spec, SessionType
        spec = _Spec(
            market_code="TEST",
            weekly={1: ("09:30", "16:00")},
            overrides={"2024-01-15": ("09:30", "13:00", SessionType.HALF_DAY)},
        )
        cal = TradingHoursCalendar(
            clock=lambda: "2024-01-15T10:00", specs={"TEST": spec}
        )
        s = cal.session_for("TEST", "2024-01-15")
        assert s is not None
        self.assertEqual(s.close_time, "13:00")

    def test_schedule_filters_closed_days(self):
        cal = TradingHoursCalendar(clock=lambda: "2024-01-15T10:00")
        sched = cal.schedule("XNYS", ["2024-01-13", "2024-01-15", "2024-01-14"])
        self.assertIsInstance(sched, MarketSchedule)
        self.assertEqual(len(sched.sessions), 1)
        self.assertEqual(sched.sessions[0].date, "2024-01-15")

    def test_schedule_session_for_lookup(self):
        cal = TradingHoursCalendar(clock=lambda: "2024-01-15T10:00")
        sched = cal.schedule("XNYS", ["2024-01-15"])
        found = sched.session_for("2024-01-15")
        self.assertIsNotNone(found)
        assert found is not None
        self.assertEqual(found.open_time, "09:30")
        self.assertIsNone(sched.session_for("2024-01-14"))

    def test_is_open_during_session(self):
        cal = TradingHoursCalendar(clock=lambda: "2024-01-15T12:00")
        self.assertTrue(cal.is_open("XNYS"))

    def test_is_open_before_open(self):
        cal = TradingHoursCalendar(clock=lambda: "2024-01-15T09:00")
        self.assertFalse(cal.is_open("XNYS"))

    def test_is_open_at_close_is_false(self):
        # 16:00 exactly is the close; we treat close as not open.
        cal = TradingHoursCalendar(clock=lambda: "2024-01-15T16:00")
        self.assertFalse(cal.is_open("XNYS"))

    def test_is_open_on_weekend(self):
        cal = TradingHoursCalendar(clock=lambda: "2024-01-13T12:00")
        self.assertFalse(cal.is_open("XNYS"))

    def test_is_open_xsau_saturday(self):
        cal = TradingHoursCalendar(clock=lambda: "2024-01-13T11:00")
        self.assertTrue(cal.is_open("XSAU"))

    def test_is_open_xsau_friday(self):
        cal = TradingHoursCalendar(clock=lambda: "2024-01-12T11:00")
        self.assertFalse(cal.is_open("XSAU"))

    def test_half_day_closed_afternoon(self):
        from trading_hours_calendar_utils.core import _Spec, SessionType
        spec = _Spec(
            market_code="TEST",
            weekly={1: ("09:30", "16:00")},
            overrides={"2024-01-15": ("09:30", "13:00", SessionType.HALF_DAY)},
        )
        cal = TradingHoursCalendar(
            clock=lambda: "2024-01-15T14:00", specs={"TEST": spec}
        )
        self.assertFalse(cal.is_open("TEST"))


if __name__ == "__main__":
    unittest.main()
