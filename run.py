"""
Run GARP Core 10 for this week: what to hold from the next open (normally Friday's).

    export TICKERDB_API_KEY=tdb_...      # https://tickerdb.com/setup
    python run.py

Schedule it once a week after TickerDB publishes Thursday's daily snapshot
(knowledge cutoff 04:00 UTC Friday), for example Friday 05:00 UTC, before the
US open. Holidays need nothing special: it decides on the newest close (Wednesday
in Thanksgiving week) and you trade at the next open (the next Monday when Friday
is a holiday), as the backtest does. Each run:

  1. Reads the yield curve band for the recent decision days (1 credit).
  2. Fetches the newest daily snapshot of every US stock (50 credits) and the
     bars of the three earlier decision days for the liquidity filter (75).
  3. Applies the rules given the holdings in state.json, prints what to sell
     and buy, and saves the new state.

About 125 credits a week, 550 a month. It never places orders, and a decision
day is decided only once.
"""
from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path

import model

HERE = Path(__file__).resolve().parent
STATE = HERE / "state.json"


def main() -> None:
    today = date.today()
    start = (today - timedelta(days=120)).isoformat()
    zones = model.curve_zones(start, today.isoformat())
    sessions = sorted(zones)
    if len(sessions) < 30:
        raise SystemExit("Not enough recent market rows; try again later.")
    decision = sessions[-1]
    # Earlier decision days: each earlier week's last session from Monday to Thursday.
    earlier = [d for d, _ in model.week_plan(sessions) if d < decision]
    state = json.loads(STATE.read_text()) if STATE.exists() else {"holdings": [], "last_decided": ""}
    if state["last_decided"] >= decision:
        print(f"{decision} already decided. Hold: {' '.join(h['ticker'] for h in state['holdings']) or model.CASH}")
        return

    curve = model.Curve()
    for d in [*earlier, decision]:
        risk_off = curve.update(zones.get(d))

    rows, credits = model.snapshot(decision)
    credits += seed_liquidity(earlier[-(model.LIQUIDITY_DAYS - 1):], rows)

    held = [h["asset_id"] for h in state["holdings"]]
    names = {h["asset_id"]: h["ticker"] for h in state["holdings"]}
    target, sells = model.decide(rows, held, risk_off)
    buys = [a for a in target if a not in held]
    names.update({a: rows[a]["ticker"] for a in target})
    STATE.write_text(json.dumps({"last_decided": decision, "curve": curve.to_json(),
                                 "holdings": [{"asset_id": a, "ticker": names[a]} for a in target]}, indent=1))

    if date.fromisoformat(decision).weekday() != 3:
        print(f"Note: the newest snapshot ({decision}) is not a Thursday. That is right only when Thursday was a "
              "market holiday; otherwise run this after Thursday's snapshot (Friday 05:00 UTC).")
    print(f"Decision day {decision} (yield curve: {zones.get(decision)}, flat {curve.flat_run} in a row)"
          + ("  RISK-OFF: hold " + model.CASH if risk_off else ""))
    for a, why in sells.items():
        print(f"  sell {names[a]:<6} {why}")
    for a in buys:
        print(f"  buy  {names[a]:<6} GARP Core {model.growth_score(rows[a]):.1f}, 1/{model.POSITIONS} of the portfolio")
    if not sells and not buys:
        print("  no change")
    print("Hold: " + (" ".join(names[a] for a in target) or model.CASH)
          + (f"  ({model.POSITIONS - len(target)} slots in {model.CASH})" if target and len(target) < model.POSITIONS else ""))
    print(f"({credits} credits)")


def seed_liquidity(days: list[str], rows: dict) -> int:
    """Set each row's dollar_volume from the earlier decision days' traded value plus today's. Returns credits."""
    liq, credits = model.Liquidity(), 0
    for d in days:
        got, c = model.history({"asset_class": "stock", "timeframe": "daily", "ohlcv": "true",
                                "adjustment": "raw", "start": d, "end": d})   # traded value as traded
        credits += c
        liq.update({r["asset_id"]: {"decision_close": r.get("ohlcv_close"), "decision_volume": r.get("ohlcv_volume")} for r in got})
    liq.update(rows)
    return credits


if __name__ == "__main__":
    main()
