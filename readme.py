"""
The README, its charts and results/ from GARP Core 10's published record: the one the model page on
tickerdb.com shows (https://tickerdb.com/model/garp-core-10). Every figure here is that record's,
written the way the page writes it (fmt.py), so the two never disagree.

    python readme.py              # fetch the record into results/record.json, then rewrite everything
    python readme.py --offline    # rewrite everything from the stored results/record.json
    python readme.py --check      # fail if the README, the charts or results/ differ from the stored record,
                                  # or backtest.py's replayed trades differ from the record's
    python readme.py --check --online   # also fail if the stored record is older than the published one

The record is the engine's run of model.py's rules at TickerDB: every session marked at its close,
dividends and splits as they happened, idle cash in BIL, 0.1% costs each way. backtest.py replays the
same rules from the TickerDB API and must make exactly the record's trades (--check, and
tests/test_record.py).
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import sys
import tempfile
import urllib.request
from pathlib import Path

import charts
import fmt

HERE = Path(__file__).resolve().parent
RESULTS = HERE / "results"
ASSETS = HERE / "assets"
RECORD = RESULTS / "record.json"
REPLAY = RESULTS / "replay-trades.csv"
DECISIONS = RESULTS / "decisions.csv"
SLUG = "garp-core-10"
NAME = "GARP Core 10"
BENCH = "S&P 500"
URL = f"https://tickerdb.com/api/model-live/{SLUG}"
START_CASH = 10_000           # the page's notional start
TAPE_ROWS = 12
#: The images readme.py draws (the "Run in" buttons are static: charts.py).
CHARTS = ("results.svg", "stats.svg", "edge.svg", "years.svg", "rolling.svg", "rolling-windows.svg", "trades.svg")
TRADE_COLUMNS = ("ticker", "side", "entry_date", "entry_price", "exit_date", "exit_price", "return_pct", "days_held",
                 "exit_reason")


# ---------------------------------------------------------------- the record
def fetch() -> dict:
    req = urllib.request.Request(URL, headers={"Accept": "application/json",
                                               "User-Agent": f"tickerdb-{SLUG}/1.0 (+https://github.com/tickerdb/{SLUG})"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.load(resp)


def load() -> dict:
    if not RECORD.exists():
        raise SystemExit(f"No {RECORD.relative_to(HERE)}. Run python readme.py first.")
    return json.loads(RECORD.read_text(encoding="utf-8"))


def record_text(record: dict) -> str:
    return json.dumps(record, indent=1, ensure_ascii=False) + "\n"


# ---------------------------------------------------------------- the page's figures
def the(bench: str) -> str:
    return f"the {bench}"


def figures(record: dict) -> dict:
    """Every figure the README prints, as the page computes and writes it."""
    bt = record["backtest"]
    s = bt["stats"]
    eq, bm = bt["equity"], bt["benchmark"]
    model_x, bench_x = eq[-1][1], bm[-1][1]
    bmap = dict(bm)
    series = [(d, v / bmap[d]) for d, v in eq if d in bmap and bmap[d] > 0]
    peak, low = series[0], series[0]
    for p in series:
        if p[1] > peak[1]:
            peak = p
        if p[1] < low[1]:
            low = p
    rest = series[1:]
    ahead = sum(v > 1 for _, v in rest) / len(rest) * 100
    edge_year = ((1 + s["cagr_pct"] / 100) / (1 + s["benchmark_cagr_pct"] / 100) - 1) * 100
    trades = bt["trades"]
    returns = [t["return_pct"] for t in trades if t.get("return_pct") is not None]
    wins = sum(r > 0 for r in returns)
    r = record["rolling_starts"]
    points = r["points"]
    best = max(points, key=lambda p: p[1])
    worst = min(points, key=lambda p: p[1])
    return {
        "start": bt["start"], "end": bt["end"], "model_x": model_x, "bench_x": bench_x,
        "roi": s["roi_pct"], "bench_roi": s["benchmark_roi_pct"], "cagr": s["cagr_pct"], "bench_cagr": s["benchmark_cagr_pct"],
        "dd": s["max_drawdown_pct"], "bench_dd": s["benchmark_max_drawdown_pct"],
        "edge_end": series[-1][1], "peak": peak, "low": low, "ahead": ahead, "edge_year": edge_year,
        "years": s["years"], "trades": trades, "trades_count": len(returns), "win_rate": wins / len(returns) * 100,
        "avg_trade": sum(returns) / len(returns), "rolling": r, "best_start": best, "worst_start": worst,
    }


def summaries(f: dict) -> dict:
    """The page's one-line summaries under its cards (src/lib/model-summaries.ts), for this model."""
    p, t = fmt.summary_pct, fmt.summary_times
    ratio = (1 + f["roi"] / 100) / (1 + f["bench_roi"] / 100) if f["roi"] > 0 and f["bench_roi"] > 0 else None
    diff = f["roi"] - f["bench_roi"]
    span = f"{p(f['roi'])} over the backtest"
    if abs(diff) < 1:
        ret = f"{NAME} returned {span}, level with {the(BENCH)}'s {p(f['bench_roi'])}."
    elif diff > 0:
        ret = (f"{NAME} returned {span}, outperforming {the(BENCH)}'s {p(f['bench_roi'])}"
               + (f" and ending {t(ratio)} its result" if ratio is not None and ratio >= 1.5 else "") + ".")
    else:
        ret = f"{NAME} returned {span}, trailing {the(BENCH)}'s {p(f['bench_roi'])}."
    faster, shallower = f["cagr"] > f["bench_cagr"], abs(f["dd"]) < abs(f["bench_dd"])
    stats = (f"{NAME} grew {'faster' if faster else 'slower'} than {the(BENCH)} ({p(f['cagr'])} vs {p(f['bench_cagr'])} a year), "
             f"with {'a shallower' if shallower else 'a deeper'} worst fall ({p(-abs(f['dd']))} vs {p(-abs(f['bench_dd']))}).")
    e, when = f["edge_end"], f"{fmt.js_round(f['ahead'])}% of the time"
    if abs(e - 1) < 0.01:
        edge = f"{NAME} ended level with {the(BENCH)}, ahead {when}."
    elif e > 1:
        edge = f"{NAME} beat {the(BENCH)} by {t(e)} and was ahead {when}."
    else:
        edge = f"{NAME} lost to {the(BENCH)}, ending with {t(e)} of its result, and was ahead only {when}."
    ys = f["years"]
    beat = sum(y["model_pct"] > y["benchmark_pct"] for y in ys)
    top = ys[0]
    for y in ys:
        if y["model_pct"] > top["model_pct"]:
            top = y
    years = f"{NAME} beat {the(BENCH)} in {beat} of {len(ys)} {'year' if len(ys) == 1 else 'years'}; its best year was {top['year']} at {p(top['model_pct'])}."
    trades = (f"{NAME} closed {f['trades_count']:,} {'trade' if f['trades_count'] == 1 else 'trades'}: {fmt.js_round(f['win_rate'])}% won, and the average trade "
              f"returned {p(f['avg_trade'])}.")
    pts = f["rolling"]["points"]
    rates = [q[1] for q in pts]
    paired = [q for q in pts if q[2] is not None]
    above = sum(q[1] > q[2] for q in paired)
    vs = (f"above {the(BENCH)}'s from every one of {len(paired):,} starts" if above == len(paired)
          else f"below {the(BENCH)}'s from every start" if above == 0
          else f"above {the(BENCH)}'s from {fmt.js_round(above / len(paired) * 100)}% of {len(paired):,} starts")
    rolling = (f"Whichever week {NAME} started, its yearly return to date ran between {p(min(rates))} and {p(max(rates))}, {vs}.")
    return {"return": ret, "stats": stats, "edge": edge, "years": years, "trades": trades, "rolling": rolling}


# ---------------------------------------------------------------- the README
def risk_off_weeks() -> tuple[int, int] | None:
    """Risk-off weeks of backtest.py's replay (results/decisions.csv), the same decisions as the record's."""
    if not DECISIONS.exists():
        return None
    with DECISIONS.open(newline="") as fh:
        rows = list(csv.DictReader(fh))
    return sum(r["risk_off"] == "1" for r in rows), len(rows)


def readme(record: dict) -> str:
    f = figures(record)
    say = summaries(f)
    sp, money, times, day = fmt.signed_pct, fmt.money, fmt.times, fmt.long_date
    r = f["rolling"]
    hz = r["horizons"]
    weeks = risk_off_weeks()
    horizon_rows = "\n".join(
        f"| {label} | {sp(h['return_pct']['median'])} | {sp(h['benchmark_return_pct']['median'])} | {fmt.share(h['beat_benchmark_pct'])} | {h['starts_count']} |"
        for key, label in (("1y", "1 year"), ("2y", "2 years"), ("3y", "3 years")) if (h := hz.get(key)))
    year_rows = "\n".join(f"| {y['year']} | {sp(y['model_pct'])} | {sp(y['benchmark_pct'])} |" for y in reversed(f["years"]))
    stats_alt = (f"Model {times(f['model_x'])}, {BENCH} {times(f['bench_x'])}. Balance {money(f['model_x'] * START_CASH)} vs "
                 f"{money(f['bench_x'] * START_CASH)}; ROI {sp(f['roi'])} vs {sp(f['bench_roi'])}; CAGR {sp(f['cagr'])} vs "
                 f"{sp(f['bench_cagr'])}; max drawdown {sp(f['dd'])} vs {sp(f['bench_dd'])}")
    edge_alt = (f"The model beat the {BENCH} by {times(f['edge_end'])}: peak {times(f['peak'][1])}, low {times(f['low'][1])}, "
                f"ahead {fmt.js_round(f['ahead'])}% of days, {sp(f['edge_year'])} a year")
    off = (f" It sat out {weeks[0]} of {weeks[1]} weeks." if weeks else "")
    return f"""<h1 align="center">{NAME}</h1>

<p align="center">An open-source trading model based on GARP principles that runs in Claude or ChatGPT.</p>

<p align="center">
  <a href="https://tickerdb.com/go/claude/{SLUG}"><img src="assets/open-in-claude.svg" alt="Run in Claude" height="44"></a>
  &nbsp;
  <a href="https://tickerdb.com/go/chatgpt/{SLUG}"><img src="assets/open-in-chatgpt.svg" alt="Run in ChatGPT" height="44"></a>
</p>

<p align="center">Click a button above, or paste this into Claude in your browser (in ChatGPT, use the button above):</p>

```
Read https://tickerdb.com/run/{SLUG} and follow its steps. Once it's set up, schedule a weekly check every Friday after 06:00 UTC that reads my model link and tells me only if the model bought or sold something.
```

<p align="center">No signup first and no API key to paste: the assistant gives you one link to approve (a free TickerDB account is created there if you are new), then shows you the model's record and checks it for you every week. Each check uses 5 TickerDB credits; the Free plan's 250 credits a month cover one daily check.</p>

<p align="center">
  Data: <a href="https://tickerdb.com">TickerDB</a>. Live record since activation: <a href="https://tickerdb.com/model/{SLUG}">tickerdb.com/model/{SLUG}</a>
</p>

<p align="center">
  <img src="assets/results.svg" alt="Balance of the model against the {BENCH.replace('&', '&amp;')} from {money(START_CASH)}, {f['start'][:4]} to {f['end'][:4]}" width="100%">
</p>

{say['return']}

## Stats

<p align="center">
  <img src="assets/stats.svg" alt="{stats_alt.replace('&', '&amp;')}" width="100%">
</p>

| | Model | {BENCH} |
|---|---:|---:|
| Balance from {money(START_CASH)} | {money(f['model_x'] * START_CASH)} | {money(f['bench_x'] * START_CASH)} |
| ROI | {sp(f['roi'])} | {sp(f['bench_roi'])} |
| CAGR | {sp(f['cagr'])} | {sp(f['bench_cagr'])} |
| Max drawdown | {sp(f['dd'])} | {sp(f['bench_dd'])} |

From {day(f['start'])} to {day(f['end'])}, valued at every daily close, after a 0.1% cost each way. Dividends count as they were paid, idle cash earns T-bills (BIL), and the {BENCH} is SPY with dividends reinvested.

{say['stats']}

## Edge

<p align="center">
  <img src="assets/edge.svg" alt="{edge_alt.replace('&', '&amp;')}" width="100%">
</p>

The model's balance over the {BENCH}'s, day by day: above 1× it was ahead.

| | |
|---|---:|
| Model beats the {BENCH} by | {times(f['edge_end'])} |
| Peak | {times(f['peak'][1])} ({day(f['peak'][0])}) |
| Low | {times(f['low'][1])} ({day(f['low'][0])}) |
| Time ahead | {fmt.js_round(f['ahead'])}% of days |
| Edge a year | {sp(f['edge_year'])} |

{say['edge']}

## Yearly ROI

<p align="center">
  <img src="assets/years.svg" alt="Calendar-year returns, model against the {BENCH.replace('&', '&amp;')}" width="100%">
</p>

| Year | Model | {BENCH} |
|---|---:|---:|
{year_rows}

{f['end'][:4]} runs to {day(f['end'])}. {say['years']}

## Rolling starts

We ran the model from every weekly start to {day(r['end_date'])}, to see whether the result depends on the start date.

<p align="center">
  <img src="assets/rolling.svg" alt="For each weekly start with at least two years to run, the model's CAGR to {r['end_date']} against the {BENCH.replace('&', '&amp;')}'s" width="100%">
</p>

| Yearly return | Model | {BENCH} |
|---|---:|---:|
| Median start | {sp(r['cagr_pct']['median'])}/yr | {sp(r['benchmark_cagr_pct']['median'])}/yr |
| Best start ({day(f['best_start'][0])}) | {sp(r['cagr_pct']['max'])}/yr | {sp(r['benchmark_cagr_pct']['max'])}/yr |
| Worst start ({day(f['worst_start'][0])}) | {sp(r['cagr_pct']['min'])}/yr | {sp(r['benchmark_cagr_pct']['min'])}/yr |
| Starts that beat the {BENCH} | {fmt.share(r['beat_benchmark_pct'])} of {r['full_runs_count']} | |

Starts with at least two years to run. {say['rolling']}

## Holding periods

The return from every weekly start after a fixed 1, 2 and 3 years.

<p align="center">
  <img src="assets/rolling-windows.svg" alt="Spread of 1, 2 and 3-year returns from every weekly start, model against the {BENCH.replace('&', '&amp;')}" width="100%">
</p>

| Held for | Model median | {BENCH} median | Beat {BENCH} | Starts |
|---|---:|---:|---:|---:|
{horizon_rows}

## Trades

<p align="center">
  <img src="assets/trades.svg" alt="The {TAPE_ROWS} most recent trades: stock, entry, exit and return" width="100%">
</p>

The {TAPE_ROWS} most recent; all {f['trades_count']} are in [`results/trades.csv`](results/trades.csv). Returns are after the 0.1% cost each way, dividends included. {say['trades']}

## Rules

Decided once a week on Thursday's close, traded at the next open, normally Friday's. When Friday is a market holiday the trade waits for the next open (usually Monday); in a week with no Thursday session it decides on Wednesday's close.

1. **Universe.** Every US stock with a market cap of at least $1B and a median traded value of at least $5M over the last four decision days.
2. **Candidate.** `fundamentals_growth_zone` is `high_growth`, `fundamentals_free_cash_flow_zone` is `moderate_surplus` or `high_surplus`, `fundamentals_revenue_growth_direction` is not `deteriorating`, `fundamentals_pe_vs_sector_zone` is `discount` or `deep_discount`, and the stock has a `garp_core_score`.
3. **Hold the 10 candidates with the highest GARP Core score**, equal weight at entry. A slot with no candidate stays in BIL (T-bills).
4. **No stop losses.** A holding leaves only when a candidate scores at least 5 points higher than it (a holding that no longer passes the growth test counts as the lowest), when its growth zone turns `shrinking` or it starts burning cash, or when its P/E moves to a premium to its sector.
5. **Risk-off.** When `macro_yield_curve_zone` has been `flat` for three decision days in a row, sell everything and hold BIL. Come back the first week it is no longer flat.

The parameters are at the top of [`model.py`](model.py).

## Run it yourself

With Claude Code, Codex, Cursor or another agent that runs code on your computer, paste this to clone the model and run it there on a schedule:

```
Clone github.com/tickerdb/{SLUG} and follow its README:
set up TickerDB using tickerdb.com/setup, then schedule run.py to run
every Friday at 05:00 UTC and tell me when it makes a trade.
```

## How the results are made

The figures above are the model's published record, the same one [its page](https://tickerdb.com/model/{SLUG}) shows: TickerDB runs these rules on its point-in-time data, marks the book at every daily close and publishes the result. [`readme.py`](readme.py) writes this README, its charts and `results/` from that record, and [`backtest.py`](backtest.py) replays the rules from the TickerDB API on its own and must make exactly the record's {f['trades_count']} trades.

```bash
export TICKERDB_API_KEY=tdb_...        # https://tickerdb.com/setup
python backtest.py                     # replays the rules on every US stock weekly since late 2019 (about 27,000 credits)
python backtest.py --offline           # reruns the replay on the cached data/
python readme.py                       # fetches the published record and rewrites the README, charts and results/
python readme.py --check               # fails if anything here differs from the record, or the replay's trades do
python run.py                          # this week's holdings
python -m unittest discover -s tests   # offline tests of the rules and the record
```

The replay needs a TickerDB plan with history from 2020 (Pro). No dependencies beyond Python 3.10+.

`run.py` costs about 125 credits a week (about 550 a month, more than the free plan's 250). It prints what to sell and buy, keeps the holdings in `state.json`, and never places orders.

Point in time: a week's decision uses only the daily snapshot of the week's last session from Monday to Thursday (knowledge cutoff 04:00 UTC the next day) and fills at the next session's open. Delisted companies stay in the history while they traded, and prices are matched by `asset_id`. A holding that stops trading is sold at its last close. Macro values are as first published.

## Caveats

- **In-sample.** The fields, the ranking, the 10 holdings and the risk-off rule were all chosen on the same 2020 to 2026 history they're tested on, so expect live results to be weaker. The rolling starts reuse that history; they show the result does not hinge on one start date, not that it holds out of sample.
- **The risk-off rule rests on a few flat-curve periods:** early 2020, February to July 2022, September 2024 to April 2025, and most of May to November 2026.{off}
- **2020 is flattered by timing.** The curve was already flat when the backtest starts, so the model sits out the Covid crash and buys in late March 2020.
- **Short history.** GARP Core scores start in 2020, so the backtest covers under seven years.
- **Coverage.** Only about half of $1B+ stocks carry a GARP Core score; the rest cannot be held.
- **Costs.** 0.1% each way, no extra slippage. Smaller stocks at the open may fill worse.
- **Delistings.** Companies delisted in 2019 and 2020 are still being completed in TickerDB, so early losers may be under-counted.
- **No sector limit.** The ten holdings can cluster in one sector.
- Not investment advice. A backtest shows how a model would have done in the past; it doesn’t predict future results.

## License

MIT. The fonts embedded in the README images (Oxanium, Inter, JetBrains Mono, in `assets/fonts/`) are under the SIL Open Font License 1.1.
"""


# ---------------------------------------------------------------- results/ and charts
def trades_csv(record: dict) -> str:
    out = io.StringIO(newline="")
    w = csv.writer(out, lineterminator="\n")
    w.writerow(TRADE_COLUMNS)
    for t in record["backtest"]["trades"]:
        w.writerow(["" if t.get(k) is None else t.get(k) for k in TRADE_COLUMNS])
    return out.getvalue()


def equity_csv(record: dict) -> str:
    bt = record["backtest"]
    bmap = dict(bt["benchmark"])
    out = io.StringIO(newline="")
    w = csv.writer(out, lineterminator="\n")
    w.writerow(["date", "model_balance", "sp500_balance"])
    for d, v in bt["equity"]:
        b = bmap.get(d)
        w.writerow([d, fmt.to_fixed(v * START_CASH, 2), "" if b is None else fmt.to_fixed(b * START_CASH, 2)])
    return out.getvalue()


def draw(record: dict, folder: Path) -> None:
    f = figures(record)
    bt = record["backtest"]
    model, bench = [(d, v) for d, v in bt["equity"]], [(d, v) for d, v in bt["benchmark"]]
    m = {"multiple": f["model_x"], "roi": f["roi"] / 100, "cagr": f["cagr"] / 100, "max_drawdown": f["dd"] / 100}
    b = {"multiple": f["bench_x"], "roi": f["bench_roi"] / 100, "cagr": f["bench_cagr"] / 100, "max_drawdown": f["bench_dd"] / 100}
    charts.results(model, bench, START_CASH, folder / "results.svg")
    charts.stats(model, bench, START_CASH, m, b, folder / "stats.svg")
    charts.edge(model, bench, m, b, folder / "edge.svg")
    charts.years({str(y["year"]): y["model_pct"] / 100 for y in f["years"]},
                 {str(y["year"]): y["benchmark_pct"] / 100 for y in f["years"]}, folder / "years.svg")
    r = f["rolling"]
    charts.rolling([{"start": d, "weeks": 10**6, "cagr": c / 100, "SPY_cagr": (s or 0) / 100} for d, c, s in r["points"]],
                   r["end_date"], folder / "rolling.svg")
    starts: dict[str, dict] = {}
    for key, h in r["horizons"].items():
        for d, mv, bv in h["returns"]:
            starts.setdefault(d, {"start": d})
            starts[d][key], starts[d][f"{key}_SPY"] = mv / 100, bv / 100
    charts.windows([starts[d] for d in sorted(starts)], folder / "rolling-windows.svg")
    charts.tape([{**t, "return_pct": t["return_pct"]} for t in f["trades"]], folder / "trades.svg", TAPE_ROWS,
                this_year=int(f["end"][:4]))


def outputs(record: dict, folder: Path) -> dict[Path, str]:
    """Every file readme.py writes, by its path in the repo, rendered into `folder` for the charts."""
    draw(record, folder)
    files = {HERE / "README.md": readme(record), RECORD: record_text(record),
             RESULTS / "trades.csv": trades_csv(record), RESULTS / "equity.csv": equity_csv(record)}
    for name in CHARTS:
        files[ASSETS / name] = (folder / name).read_text(encoding="utf-8")
    return files


# ---------------------------------------------------------------- the check
def trade_keys(rows) -> list[tuple[str, str, str]]:
    return sorted((r["ticker"], r["entry_date"], r["exit_date"]) for r in rows)


def replay_differences(record: dict) -> list[str]:
    """backtest.py's replayed trades against the record's: every (ticker, entry, exit) must match."""
    if not REPLAY.exists():
        return [f"{REPLAY.relative_to(HERE)} is missing: run python backtest.py"]
    with REPLAY.open(newline="") as fh:
        replay = trade_keys(csv.DictReader(fh))
    published = trade_keys(record["backtest"]["trades"])
    if replay == published:
        return []
    only_r = sorted(set(replay) - set(published))[:5]
    only_p = sorted(set(published) - set(replay))[:5]
    return [f"replayed trades differ from the record: {len(replay)} vs {len(published)}; "
            f"only in the replay {only_r}, only in the record {only_p}"]


def check(online: bool) -> list[str]:
    problems: list[str] = []
    record = load()
    if online:
        live = fetch()
        if record_text(live) != record_text(record):
            problems.append(f"{RECORD.relative_to(HERE)} is not the published record: run python readme.py")
    with tempfile.TemporaryDirectory() as tmp:
        for path, text in outputs(record, Path(tmp)).items():
            stored = path.read_text(encoding="utf-8") if path.exists() else None
            if stored != text:
                problems.append(f"{path.relative_to(HERE)} differs from the record: run python readme.py --offline")
    problems += replay_differences(record)
    return problems


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0].strip())
    ap.add_argument("--offline", action="store_true", help="use the stored results/record.json")
    ap.add_argument("--check", action="store_true", help="only check; write nothing")
    ap.add_argument("--online", action="store_true", help="with --check: also compare with the published record")
    a = ap.parse_args()
    if a.check:
        problems = check(a.online)
        for p in problems:
            print("MISMATCH:", p)
        if problems:
            sys.exit(1)
        print("README, charts and results/ match the record; the replay makes the record's trades.")
        return
    record = load() if a.offline else fetch()
    RESULTS.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        for path, text in outputs(record, Path(tmp)).items():
            path.write_text(text, encoding="utf-8", newline="\n")
    f = figures(record)
    print(f"{NAME}, {f['start']} to {f['end']}: ROI {fmt.signed_pct(f['roi'])}, CAGR {fmt.signed_pct(f['cagr'])}, "
          f"max drawdown {fmt.signed_pct(f['dd'])}, {f['trades_count']} trades ({BENCH}: ROI {fmt.signed_pct(f['bench_roi'])}).")
    problems = replay_differences(record)
    for p in problems:
        print("MISMATCH:", p)
    if problems:
        sys.exit(1)


if __name__ == "__main__":
    main()
