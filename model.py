"""
GARP Core 10: the rules, and the TickerDB data they run on.

The idea: own growing companies only while they are cheap against their sector
and throwing off cash, and pick among them with TickerDB's GARP Core score.

Rules, decided once a week on Thursday's close and traded at the next open (normally Friday's;
Wednesday's close in a week with no Thursday session, the next Monday's open when Friday is a holiday):
  1. Universe: every US stock with a market cap of at least $1B and a median
     traded value of at least $5M over the last four decision days.
  2. Candidate: growth zone `high_growth`, free cash flow in `moderate_surplus`
     or `high_surplus`, revenue growth not `deteriorating`, P/E at a `discount`
     or `deep_discount` to its sector, and a GARP Core score.
  3. Hold the 10 candidates with the highest GARP Core score, equal weight at
     entry. A slot with no candidate stays in BIL (T-bills).
  4. No stop losses. A holding leaves only when
       - a candidate scores at least 5 points higher than it (it is pushed out;
         a holding that no longer passes the growth test counts as lowest), or
       - its growth zone turns `shrinking` or it starts burning cash, or
       - its P/E moves to a premium to its sector.
  5. Risk-off: when the yield curve band (`macro_yield_curve_zone`) has been
     `flat` for three decision days in a row, sell everything and hold BIL.
     Return the first week it is no longer flat.

Used by backtest.py (history since 2020) and run.py (this week's decision).
Source: https://github.com/tickerdb/garp-core-10
Live record since activation: https://tickerdb.com/model/garp-core-10
"""
from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from statistics import median

API = os.environ.get("TICKERDB_API_BASE", "https://api.tickerdb.com/v1").rstrip("/")
CASH = "BIL"
BENCHMARKS = ("SPY", "QQQ")

# ---------------------------------------------------------------- parameters
POSITIONS = 10
MIN_MARKET_CAP = 1e9          # USD
MIN_DOLLAR_VOLUME = 5e6       # USD, median of the last LIQUIDITY_DAYS decision days
LIQUIDITY_DAYS = 4
PUSH_OUT_MARGIN = 5.0         # GARP Core points a challenger must lead the weakest holding by
FLAT_WEEKS_IN = 3             # flat decision days in a row before going risk-off
FLAT_WEEKS_OUT = 1            # non-flat decision days in a row before coming back

GROWTH = "high_growth"
CASH_SURPLUS = frozenset({"moderate_surplus", "high_surplus"})
CASH_BURN = frozenset({"low_burn", "moderate_burn", "high_burn"})
SECTOR_CHEAP = frozenset({"discount", "deep_discount"})
SECTOR_EXPENSIVE = frozenset({"premium", "deep_premium"})

# Every field the model reads (daily timeframe), by its TickerDB name.
FIELDS = [
    "market_cap_usd",
    "garp_core_score",
    "garp_core_eligible",
    "fundamentals_growth_zone",
    "fundamentals_free_cash_flow_zone",
    "fundamentals_revenue_growth_direction",
    "fundamentals_pe_vs_sector_zone",
]
CURVE_FIELD = "macro_yield_curve_zone"


# ---------------------------------------------------------------- rules
def _num(v) -> float | None:
    try:
        x = float(v)
    except (TypeError, ValueError):
        return None
    return x if x == x else None


def _true(v) -> bool:
    return v is True or str(v).lower() == "true"


def growth_score(row: dict) -> float | None:
    """The GARP Core score if the stock still passes the growth test, else None."""
    score = _num(row.get("garp_core_score"))
    direction = row.get("fundamentals_revenue_growth_direction")
    ok = (
        score is not None
        and _true(row.get("garp_core_eligible"))
        and row.get("fundamentals_growth_zone") == GROWTH
        and row.get("fundamentals_free_cash_flow_zone") in CASH_SURPLUS
        and direction not in (None, "", "deteriorating")
    )
    return score if ok else None


def in_universe(row: dict) -> bool:
    cap, traded = _num(row.get("market_cap_usd")), _num(row.get("dollar_volume"))
    return bool(cap is not None and cap >= MIN_MARKET_CAP and traded is not None and traded >= MIN_DOLLAR_VOLUME
                and _num(row.get("decision_close")))


def is_candidate(row: dict) -> bool:
    return in_universe(row) and growth_score(row) is not None and row.get("fundamentals_pe_vs_sector_zone") in SECTOR_CHEAP


def thesis_exit(row: dict) -> str | None:
    if row.get("fundamentals_growth_zone") == "shrinking" or row.get("fundamentals_free_cash_flow_zone") in CASH_BURN:
        return "growth broken"
    if row.get("fundamentals_pe_vs_sector_zone") in SECTOR_EXPENSIVE:
        return "no longer cheap"
    return None


def decide(rows: dict, holdings: list, risk_off: bool, tradable=lambda asset: True) -> tuple[list, dict]:
    """One weekly decision.
    rows: {asset_id: row} for the decision day; holdings: asset ids held now.
    tradable(asset): whether the asset can be bought at the fill (it has a bar).
    Returns (asset ids to hold, {asset id sold: reason})."""
    sells: dict = {}
    scores: dict = {}
    for a in holdings:
        row = rows.get(a)
        if row is None:
            sells[a] = "stopped trading"
        elif risk_off:
            sells[a] = "risk-off"
        elif thesis_exit(row):
            sells[a] = thesis_exit(row)
        else:
            s = growth_score(row)
            scores[a] = s if s is not None else float("-inf")
    if risk_off:
        return [], sells
    held = set(holdings)
    queue = sorted(((a, r) for a, r in rows.items() if a not in held and is_candidate(r) and tradable(a)),
                   key=lambda x: (-growth_score(x[1]), str(x[1].get("ticker"))))
    slots = POSITIONS - len(scores)
    buys = [a for a, _ in queue[:max(slots, 0)]]
    for a, r in queue[len(buys):]:
        if not scores:
            break
        weakest = min(scores, key=scores.get)       # ties: the earliest holding
        if growth_score(r) < scores[weakest] + PUSH_OUT_MARGIN:
            break
        sells[weakest] = "pushed out"
        del scores[weakest]
        buys.append(a)
    return [a for a in holdings if a not in sells] + buys, sells


class Curve:
    """Risk-off state from the weekly yield curve band. Feed decision days in order."""

    def __init__(self, flat_run: int = 0, clear_run: int = 0, risk_off: bool = False):
        self.flat_run, self.clear_run, self.risk_off = flat_run, clear_run, risk_off

    def update(self, zone: str | None) -> bool:
        flat = zone == "flat"
        self.flat_run = self.flat_run + 1 if flat else 0
        self.clear_run = self.clear_run + 1 if not flat else 0
        if not self.risk_off and self.flat_run >= FLAT_WEEKS_IN:
            self.risk_off = True
        elif self.risk_off and self.clear_run >= FLAT_WEEKS_OUT:
            self.risk_off = False
        return self.risk_off

    def to_json(self) -> dict:
        return {"flat_run": self.flat_run, "clear_run": self.clear_run, "risk_off": self.risk_off}


class Liquidity:
    """Median traded value (raw close x volume, as traded) over each stock's last LIQUIDITY_DAYS decision days."""

    def __init__(self):
        self.recent: dict = {}

    def update(self, rows: dict) -> None:
        for a, r in rows.items():
            close, volume = _num(r.get("decision_close")), _num(r.get("decision_volume"))
            q = self.recent.setdefault(a, [])
            q.append(close * volume if close is not None and volume is not None else None)
            del q[:-LIQUIDITY_DAYS]
            known = [v for v in q if v is not None]
            r["dollar_volume"] = median(known) if len(known) >= 2 else None


# ---------------------------------------------------------------- data
def api_key() -> str:
    key = os.environ.get("TICKERDB_API_KEY", "").strip()
    if not key:
        raise SystemExit("Set TICKERDB_API_KEY (free key: see https://tickerdb.com/setup).")
    return key


class TooExpensive(Exception):
    """The API refused one page as over the plan's per-query limits."""


def get(path: str, params: dict | None = None) -> dict:
    url = f"{API}{path}" + ("?" + urllib.parse.urlencode(params) if params else "")
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {api_key()}", "Accept": "application/json",
                                                "User-Agent": "tickerdb-garp-core-10/1.0 (+https://github.com/tickerdb/garp-core-10)"})
    for attempt in range(8):
        try:
            with urllib.request.urlopen(req, timeout=300) as resp:
                return json.load(resp)
        except urllib.error.HTTPError as e:
            body = e.read().decode(errors="replace")
            if e.code in (429, 500, 502, 503, 504) and attempt < 7:
                time.sleep(int(e.headers.get("Retry-After") or 10))
                continue
            if e.code == 422 and "query_too_expensive" in body:
                raise TooExpensive(body[:300])
            raise SystemExit(f"TickerDB {e.code} on {path}: {body[:500]}")
        except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
            if attempt == 7:
                raise SystemExit(f"TickerDB network error on {path}: {e}")
            time.sleep(10)
    raise AssertionError("unreachable")


def history(params: dict) -> tuple[list[dict], int]:
    """Every row of one /v1/history request (all pages). Returns (rows, credits).
    A page refused as too expensive is retried with a smaller page."""
    limit = int(params.get("limit") or 0)
    while True:
        try:
            page = get("/history", params)
            credits = int((page.get("cost") or {}).get("credits") or 0)
            rows: list[dict] = []
            tokens = list(page.get("page_tokens") or [])
            while True:
                rows += page.get("rows", [])
                if page.get("next_page_token"):
                    page = get("/history", {**params, "page_token": page["next_page_token"]})
                elif tokens:
                    page = get("/history", {**params, "page_token": tokens.pop(0)})
                else:
                    return rows, credits
        except TooExpensive:
            limit = 1000 if not limit else limit // 2
            if limit < 250:
                raise SystemExit(f"TickerDB refused the request even at 250 rows a page: {params}")
            params = {**params, "limit": limit}
            time.sleep(3)


def snapshot(day: str) -> tuple[dict, int]:
    """Every stock on one day: the model's fields plus the day's bar as traded (raw), keyed by asset_id.
    The bar only feeds the liquidity filter, which needs the real traded value: an adjusted close times
    the day's volume understates it by every later dividend and split (GSBD in 2021: $3.1M, not $6.6M)."""
    rows, credits = history({"asset_class": "stock", "timeframe": "daily", "fields": ",".join(FIELDS), "ohlcv": "true",
                             "adjustment": "raw", "start": day, "end": day})
    return {r["asset_id"]: {**{k: r.get(k) for k in ("ticker", *FIELDS)}, "decision_close": r.get("ohlcv_close"),
                            "decision_volume": r.get("ohlcv_volume")} for r in rows}, credits


def bars(day: str) -> tuple[dict, int]:
    """Every stock's bar on one day: {asset_id: (open, close, ticker)}."""
    rows, credits = history({"asset_class": "stock", "timeframe": "daily", "ohlcv": "true",
                             "adjustment": "split_dividend", "start": day, "end": day})
    return {r["asset_id"]: (r.get("ohlcv_open"), r.get("ohlcv_close"), r.get("ticker")) for r in rows}, credits


def daily_bars(tickers: list[str], start: str, end: str) -> list[dict]:
    rows, _ = history({"tickers": ",".join(tickers), "timeframe": "daily", "ohlcv": "true",
                       "adjustment": "split_dividend", "start": start, "end": end})
    return rows


def curve_zones(start: str, end: str) -> dict[str, str]:
    """{date: macro_yield_curve_zone} for every session in the range."""
    out: dict[str, str] = {}
    cur = start
    while cur <= end:
        page = get("/market", {"timeframe": "daily", "start": cur, "end": end, "fields": CURVE_FIELD,
                               "order": "asc", "limit": 2000})
        rows = page.get("rows") or []
        for r in rows:
            out[r["date"]] = r.get(CURVE_FIELD)
        if len(rows) < 2000:
            break
        cur = max(out)
    return out


def week_plan(sessions: list[str]) -> list[tuple[str, str]]:
    """(decision day, fill day) per week: the week's last session from Monday to Thursday (normally
    Thursday; Wednesday in Thanksgiving week) and the next session after it (normally Friday; the
    next Monday or later when Friday is a holiday). A decision day with no session after it yet is
    skipped, as is a week still in progress (its next session is another Monday-to-Thursday one)."""
    from datetime import date
    out = []
    for i in range(len(sessions) - 1):
        d, nxt = date.fromisoformat(sessions[i]), date.fromisoformat(sessions[i + 1])
        if d.weekday() <= 3 and (nxt.weekday() == 4 or nxt.isocalendar()[:2] != d.isocalendar()[:2]):
            out.append((sessions[i], sessions[i + 1]))
    return out
