"""
Replay GARP Core 10's rules on TickerDB daily data, 2020 to today: the trades they make.

    export TICKERDB_API_KEY=tdb_...      # https://tickerdb.com/setup
    python backtest.py                   # fetch the data, then replay
    python backtest.py --offline         # replay again on the cached data/

The fetch makes, per week, two /v1/history requests for every US stock:
  - the decision day (normally Thursday): 7 fields plus the day's bar as traded (raw, for the
    liquidity filter's traded value), 50 credits;
  - the fill day (normally Friday; the next Monday when Friday is a holiday): the day's bar, 25 credits;
about 27,000 credits for 2020 to today, plus a few for SPY/QQQ/BIL bars and the
yield curve band. History from 2020 needs a plan that includes it (Pro: 2019 on).
Weeks are cached in data/weeks/, so an interrupted fetch resumes.

Point in time: the decision for a week uses only the daily snapshot of the
week's last session from Monday to Thursday (knowledge cutoff 04:00 UTC the
next day) and fills at the open of the next session. Delisted companies stay
in the history while they traded; prices are matched by asset_id. A holding
that stops trading is sold at the next weekly decision that has no row for it,
at its last close (as the engine does); a fill day with no bar alone sells
nothing. Costs: 10 bp per side.

Writes results/replay-trades.csv (each closed trade's ticker, entry, exit and reason) and
results/decisions.csv, and checks the trades against the published record (results/record.json,
written by readme.py): they must be exactly the same. The performance figures are the record's,
valued at every daily close with dividends (readme.py); this replay values nothing.
"""
from __future__ import annotations

import argparse
import csv
import gzip
import json
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from pathlib import Path

import model

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"
RESULTS = HERE / "results"
START = "2020-01-01"       # first fill day on or after this date
WARMUP = "2019-11-01"      # earlier weeks only seed the liquidity filter and the yield curve state
COST = 0.001               # 10 bp per side
START_CASH = 100_000.0
ROW_KEYS = ["ticker", *model.FIELDS, "decision_close", "decision_volume", "fill_open", "fill_close"]


# ---------------------------------------------------------------- data
def _f(v) -> float | None:
    try:
        x = float(v)
    except (TypeError, ValueError):
        return None
    return x if x == x and x > 0 else None


def fetch_week(decision: str, fill: str) -> int:
    out = DATA / "weeks" / f"{fill}.json.gz"
    if out.exists():
        return 0
    snap, c1 = model.snapshot(decision)
    bar, c2 = model.bars(fill)
    rows = {}
    for a in set(snap) | set(bar):
        r = dict(snap.get(a) or {})
        o, c, ticker = bar.get(a, (None, None, None))
        r.update(fill_open=o, fill_close=c)
        r.setdefault("ticker", ticker)
        rows[a] = r
    tmp = out.with_suffix(".tmp")
    with gzip.open(tmp, "wt", encoding="utf-8", compresslevel=4) as f:
        json.dump({"decision": decision, "fill": fill, "rows": rows}, f)
    tmp.replace(out)
    return c1 + c2


def unpack_cached(weeks: list[tuple[str, str]]) -> None:
    """Seed data/weeks/ from data/weeks.csv.gz for every planned week it already holds with the same
    decision day, so a fetch only spends credits on new or changed weeks."""
    src = DATA / "weeks.csv.gz"
    if not src.exists():
        return
    plan = dict((fl, d) for d, fl in weeks)
    cached: dict[str, dict] = {}
    with gzip.open(src, "rt", newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            fl = r["fill_date"]
            if plan.get(fl) == r["decision_date"] and not (DATA / "weeks" / f"{fl}.json.gz").exists():
                cached.setdefault(fl, {})[r["asset_id"]] = {k: (None if r[k] == "" else r[k]) for k in ROW_KEYS}
    for fl, rows in cached.items():
        with gzip.open(DATA / "weeks" / f"{fl}.json.gz", "wt", encoding="utf-8", compresslevel=4) as f:
            json.dump({"decision": plan[fl], "fill": fl, "rows": rows}, f)


def fetch(end: str) -> None:
    (DATA / "weeks").mkdir(parents=True, exist_ok=True)
    bench = model.daily_bars([model.CASH, *model.BENCHMARKS], WARMUP, end)
    with gzip.open(DATA / "bench.csv.gz", "wt", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["ticker", "date", "open"])
        w.writerows([r["ticker"], r["date"], r["ohlcv_open"]] for r in bench)
    sessions = sorted({r["date"] for r in bench if r["ticker"] == "SPY"})
    weeks = model.week_plan(sessions)
    zones = model.curve_zones(WARMUP, end)
    with (DATA / "curve.csv").open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["date", model.CURVE_FIELD])
        w.writerows(sorted(zones.items()))
    unpack_cached(weeks)
    credits = 0
    with ThreadPoolExecutor(3) as ex:
        for i, c in enumerate(ex.map(lambda p: fetch_week(*p), weeks), 1):
            credits += c
            if i % 50 == 0:
                print(f"{i}/{len(weeks)} weeks, {credits} credits", flush=True)
    print(f"fetched {len(weeks)} weeks, {credits} credits")
    with gzip.open(DATA / "weeks.csv.gz", "wt", newline="", encoding="utf-8", compresslevel=4) as f:
        w = csv.writer(f)
        w.writerow(["fill_date", "decision_date", "asset_id", *ROW_KEYS])
        for d, fl in weeks:
            with gzip.open(DATA / "weeks" / f"{fl}.json.gz", "rt", encoding="utf-8") as g:
                rows = json.load(g)["rows"]
            for a in sorted(rows, key=int):
                w.writerow([fl, d, a, *("" if rows[a].get(k) is None else rows[a].get(k) for k in ROW_KEYS)])


def load() -> tuple[list[tuple[str, str, dict]], dict, dict]:
    """Returns (weeks [(decision day, fill day, {asset_id: row})], bench {ticker: {date: open}}, curve {date: zone})."""
    for name in ("weeks.csv.gz", "bench.csv.gz", "curve.csv"):
        if not (DATA / name).exists():
            raise SystemExit(f"No cached data at {DATA / name}. Run without --offline first.")
    weeks: dict[str, tuple[str, dict]] = {}
    with gzip.open(DATA / "weeks.csv.gz", "rt", newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            row = {k: (None if r[k] == "" else r[k]) for k in ROW_KEYS}
            weeks.setdefault(r["fill_date"], (r["decision_date"], {}))[1][r["asset_id"]] = row
    bench: dict[str, dict[str, float]] = {}
    with gzip.open(DATA / "bench.csv.gz", "rt", newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            bench.setdefault(r["ticker"], {})[r["date"]] = float(r["open"])
    with (DATA / "curve.csv").open(newline="") as f:
        curve = {r["date"]: r[model.CURVE_FIELD] for r in csv.DictReader(f)}
    return [(weeks[fl][0], fl, weeks[fl][1]) for fl in sorted(weeks)], bench, curve


# ---------------------------------------------------------------- simulation
def simulate(weeks: list, bench: dict, curve: dict) -> dict:
    liquidity, state = model.Liquidity(), model.Curve()
    cash_px = bench[model.CASH]
    cash = START_CASH
    held: dict[str, dict] = {}      # asset -> {ticker, shares, entry, entry_date, last}
    equity, trades, decisions = [], [], []
    prev_fill = None
    for decision, fill, rows in weeks:
        liquidity.update(rows)
        risk_off = state.update(curve.get(decision))
        if fill < START:
            continue
        if prev_fill and cash_px.get(fill) and cash_px.get(prev_fill):
            cash *= cash_px[fill] / cash_px[prev_fill]
        prev_fill = fill
        # Mark the book at the fill's open; a holding with no bar is valued at its last close.
        price, stale = {}, set()
        for a, h in held.items():
            o = _f((rows.get(a) or {}).get("fill_open"))
            price[a] = o or h["last"]
            if not o:
                stale.add(a)
        total = cash + sum(h["shares"] * price[a] for a, h in held.items())
        equity.append({"date": fill, "equity": round(total, 2), "cash_pct": round(cash / total * 100, 1), "holdings": len(held)})

        # The decision reads the decision day's rows only: a holding is "stopped trading" once that day has no
        # row for it. A sell on a fill day with no bar goes at the last close (the engine's rule).
        decided = {a: r for a, r in rows.items() if r.get("decision_close") is not None}
        target, sells = model.decide(decided, list(held), risk_off, tradable=lambda a: _f(rows[a].get("fill_open")) is not None)
        for a, why in sells.items():
            h = held.pop(a)
            cash += h["shares"] * price[a] * (1 - COST)
            trades.append({"ticker": h["ticker"], "entry_date": h["entry_date"], "entry_price": round(h["entry"], 4),
                           "exit_date": fill, "exit_price": round(price[a], 4),
                           "return_pct": round((price[a] / h["entry"] - 1) * 100, 2), "exit_reason": why})
        total = cash + sum(h["shares"] * price[a] for a, h in held.items())
        buys = [a for a in target if a not in held]
        for a in buys:
            px = _f(rows[a]["fill_open"])
            spend = min(cash, total / model.POSITIONS)
            if spend <= 1:
                break
            cash -= spend
            held[a] = {"ticker": rows[a]["ticker"], "shares": spend * (1 - COST) / px, "entry": px, "entry_date": fill, "last": px}
        for a, h in held.items():
            c = _f((rows.get(a) or {}).get("fill_close"))
            if c:
                h["last"] = c
        decisions.append({"decision_date": decision, "fill_date": fill, "risk_off": int(risk_off),
                          "sell": " ".join(t["ticker"] for t in trades[len(trades) - len(sells):]),
                          "buy": " ".join(rows[a]["ticker"] for a in buys if a in held),
                          "holdings": " ".join(h["ticker"] for h in held.values()) or model.CASH})
    return {"equity": equity, "trades": trades, "decisions": decisions,
            "open": [{"ticker": h["ticker"], "entry_date": h["entry_date"], "entry_price": round(h["entry"], 4),
                      "last_close": round(h["last"], 4)} for h in held.values()]}


# ---------------------------------------------------------------- output
def replay_rows(res: dict) -> list[dict]:
    """The replay's closed trades by what identifies them: no prices or returns, which are the record's
    (valued at every daily close with dividends; readme.py)."""
    return [{"ticker": t["ticker"], "entry_date": t["entry_date"], "exit_date": t["exit_date"],
             "exit_reason": t["exit_reason"]} for t in res["trades"]]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--offline", action="store_true")
    ap.add_argument("--end", default=date.today().isoformat())
    a = ap.parse_args()
    if not a.offline:
        fetch(a.end)
    weeks, bench, curve = load()
    res = simulate(weeks, bench, curve)
    RESULTS.mkdir(exist_ok=True)
    for name, rows in (("replay-trades", replay_rows(res)), ("decisions", res["decisions"])):
        with (RESULTS / f"{name}.csv").open("w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator="\n")
            w.writeheader()
            w.writerows(rows)
    d = res["decisions"]
    off = sum(x["risk_off"] for x in d)
    print(f"Replayed {d[0]['fill_date']} to {d[-1]['fill_date']}: {len(res['trades'])} closed trades, "
          f"risk-off {off} of {len(d)} weeks, holding now: {' '.join(h['ticker'] for h in res['open']) or model.CASH}.")
    print("Wrote results/replay-trades.csv and results/decisions.csv.")
    import readme
    if readme.RECORD.exists():
        problems = readme.replay_differences(readme.load())
        if problems:
            print("MISMATCH:", *problems)
            raise SystemExit(1)
        print("The replay makes exactly the published record's trades.")


if __name__ == "__main__":
    main()
