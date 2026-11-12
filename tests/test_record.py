"""The README, its charts and results/ must be the published record's, and the replay must make the
record's trades. Offline: it reads results/record.json, the stored copy of the record."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import fmt  # noqa: E402
import readme  # noqa: E402


class Record(unittest.TestCase):
    def test_everything_matches_the_record(self):
        self.assertEqual(readme.check(online=False), [])

    def test_the_replay_makes_the_records_trades(self):
        self.assertEqual(readme.replay_differences(readme.load()), [])


class PageFormatting(unittest.TestCase):
    """fmt.py writes figures as the page's JavaScript does (toFixed and Math.round take a tie up)."""

    def test_signed_pct(self):
        self.assertEqual(fmt.signed_pct(573.098795), "+573%")
        self.assertEqual(fmt.signed_pct(-18.182106), "-18%")
        self.assertEqual(fmt.signed_pct(8.67), "+8.7%")
        self.assertEqual(fmt.signed_pct(9.96), "+10.0%")      # one decimal below 10, whatever it rounds to
        self.assertEqual(fmt.signed_pct(10039.4), "+10,039%")
        self.assertEqual(fmt.signed_pct(-0.04), "0.0%")
        self.assertEqual(fmt.signed_pct(0.25), "+0.3%")       # 0.25 is exact in binary: a tie, taken up
        self.assertEqual(fmt.signed_pct(None), "-")

    def test_money_times_and_dates(self):
        self.assertEqual(fmt.money(67309.88), "$67,310")
        self.assertEqual(fmt.money(2.5), "$3")                # Math.round(2.5) is 3, Python's round() gives 2
        self.assertEqual(fmt.times(6.730988), "6.73×")
        self.assertEqual(fmt.times(12.34), "12.3×")
        self.assertEqual(fmt.summary_times(2.702), "2.7×")
        self.assertEqual(fmt.summary_pct(-18.18), "−18%")
        self.assertEqual(fmt.share(77.45), "77%")
        self.assertEqual(fmt.long_date("2026-05-05"), "May 5, 2026")


if __name__ == "__main__":
    unittest.main()
