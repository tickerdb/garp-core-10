"""Offline tests of the rules on small synthetic rows.   python -m unittest discover -s tests"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import model  # noqa: E402


def row(ticker, score, **kw):
    r = {"ticker": ticker, "market_cap_usd": 5e9, "dollar_volume": 2e7, "decision_close": 50.0,
         "garp_core_score": score, "garp_core_eligible": True, "fundamentals_growth_zone": "high_growth",
         "fundamentals_free_cash_flow_zone": "high_surplus", "fundamentals_revenue_growth_direction": "steady",
         "fundamentals_pe_vs_sector_zone": "discount"}
    r.update(kw)
    return r


class Rules(unittest.TestCase):
    def test_candidate_gates(self):
        self.assertTrue(model.is_candidate(row("A", 80)))
        self.assertFalse(model.is_candidate(row("A", 80, market_cap_usd=5e8)))
        self.assertFalse(model.is_candidate(row("A", 80, dollar_volume=1e6)))
        self.assertFalse(model.is_candidate(row("A", 80, fundamentals_growth_zone="moderate_growth")))
        self.assertFalse(model.is_candidate(row("A", 80, fundamentals_free_cash_flow_zone="low_surplus")))
        self.assertFalse(model.is_candidate(row("A", 80, fundamentals_revenue_growth_direction="deteriorating")))
        self.assertFalse(model.is_candidate(row("A", 80, fundamentals_pe_vs_sector_zone="aligned")))
        self.assertFalse(model.is_candidate(row("A", None)))
        self.assertFalse(model.is_candidate(row("A", 80, garp_core_eligible=False)))

    def test_fills_top_scores_and_leaves_empty_slots(self):
        rows = {i: row(f"T{i:02d}", 60 + i) for i in range(4)}
        target, sells = model.decide(rows, [], False)
        self.assertEqual(target, [3, 2, 1, 0])
        self.assertEqual(sells, {})

    def test_push_out_needs_the_margin(self):
        rows = {i: row(f"T{i:02d}", 70) for i in range(model.POSITIONS)}
        held = list(rows)
        rows[98] = row("NEAR", 70 + model.PUSH_OUT_MARGIN - 0.1)
        self.assertEqual(model.decide(rows, held, False), (held, {}))
        rows[99] = row("FAR", 70 + model.PUSH_OUT_MARGIN)
        target, sells = model.decide(rows, held, False)
        self.assertEqual(sells, {0: "pushed out"})
        self.assertEqual(target, held[1:] + [99])

    def test_no_stop_loss_but_thesis_exits(self):
        rows = {1: row("KEEP", 40), 2: row("BURN", 90, fundamentals_free_cash_flow_zone="low_burn"),
                3: row("RICH", 90, fundamentals_pe_vs_sector_zone="premium"), 4: row("FADE", 90, fundamentals_growth_zone="stable")}
        target, sells = model.decide(rows, [1, 2, 3, 4, 5], False)
        self.assertEqual(sells, {2: "growth broken", 3: "no longer cheap", 5: "stopped trading"})
        self.assertEqual(target, [1, 4])      # a low score or a faded growth zone alone never sells

    def test_faded_holding_is_first_pushed_out(self):
        rows = {i: row(f"T{i:02d}", 70) for i in range(model.POSITIONS)}
        rows[4]["fundamentals_growth_zone"] = "stable"
        rows[50] = row("NEW", 30)
        target, sells = model.decide(rows, list(range(model.POSITIONS)), False)
        self.assertEqual(sells, {4: "pushed out"})
        self.assertIn(50, target)

    def test_risk_off_sells_everything(self):
        rows = {i: row(f"T{i:02d}", 70) for i in range(3)}
        target, sells = model.decide(rows, [0, 1], True)
        self.assertEqual(target, [])
        self.assertEqual(sells, {0: "risk-off", 1: "risk-off"})

    def test_curve_confirmation(self):
        c = model.Curve()
        self.assertEqual([c.update(z) for z in ["flat", "flat", "normal", "flat", "flat", "flat", "flat", "inverted", "flat"]],
                         [False, False, False, False, False, True, True, False, False])

    def test_liquidity_median(self):
        liq = model.Liquidity()
        r = {}
        for close, volume in ((10, 100), (10, 300), (10, 200), (10, 1000), (10, 5000)):
            r = {1: {"decision_close": close, "decision_volume": volume}}
            liq.update(r)
        self.assertEqual(r[1]["dollar_volume"], 6500.0)    # median of 3000, 2000, 10000, 50000

    def test_week_plan_waits_for_the_next_open_on_holidays(self):
        sessions = ["2026-03-26", "2026-03-27",                          # Thursday, Friday
                    "2026-03-30", "2026-03-31", "2026-04-01", "2026-04-02",  # Good Friday 04-03 closed
                    "2026-04-06", "2026-04-07"]
        self.assertEqual(model.week_plan(sessions), [
            ("2026-03-26", "2026-03-27"),     # normal week: Thursday close, Friday open
            ("2026-04-02", "2026-04-06"),     # Good Friday: Thursday close, Monday open
        ])
        thanksgiving = ["2026-11-23", "2026-11-24", "2026-11-25", "2026-11-27", "2026-11-30"]   # 11-26 closed
        self.assertEqual(model.week_plan(thanksgiving), [("2026-11-25", "2026-11-27")])
        self.assertEqual(model.week_plan(["2026-10-27", "2026-10-28"]), [])   # week still in progress


if __name__ == "__main__":
    unittest.main()
