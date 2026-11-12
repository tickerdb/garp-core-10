"""
How the model page on tickerdb.com writes its figures, so the README and its charts print exactly the
same text from the same published record (tickerdb.com: src/lib/model-live.ts signedPct and longDate,
src/components/ModelView.astro money and times, src/lib/model-summaries.ts).

JavaScript rounds differently from Python's round(): Number.toFixed takes the nearer decimal of the
exact binary value and, on a tie, the one further from zero; Math.round takes a tie up. Both are
reproduced here with Decimal, never with round() or a format spec.
"""
from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal
import math

MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")


def to_fixed(v: float, digits: int) -> str:
    """JavaScript's v.toFixed(digits), without the thousands separator."""
    q = Decimal(abs(v)).quantize(Decimal(1).scaleb(-digits), rounding=ROUND_HALF_UP)
    text = f"{q:.{digits}f}"
    return ("-" + text) if v < 0 and q != 0 else text


def js_round(v: float) -> int:
    """JavaScript's Math.round: a tie goes up."""
    return math.floor(v + 0.5)


def _group(text: str) -> str:
    """Thousands separators on a plain decimal string, as toLocaleString('en-US') writes them."""
    sign, text = ("-", text[1:]) if text.startswith("-") else ("", text)
    whole, _, frac = text.partition(".")
    whole = f"{int(whole):,}"
    return sign + whole + ("." + frac if frac else "")


def signed_pct(v: float | None, digits: int | None = None) -> str:
    """The page's signedPct: "+4.2%", "-1.8%", "+573%", "+10,039%"; one decimal under 10%, whole
    percents from 10%; "-" for none."""
    if v is None:
        return "-"
    if digits is None:
        digits = 0 if abs(v) >= 10 else 1
    text = to_fixed(v, digits)
    r = float(text)
    if r == 0:
        text = to_fixed(0.0, digits)
    return ("+" if r > 0 else "") + _group(text) + "%"


def summary_pct(v: float) -> str:
    """The page's one-line summaries' percent: a true minus sign, whole percents with separators from
    100%, otherwise one decimal under 10%."""
    sign = "+" if v > 0 else "−" if v < 0 else ""
    a = abs(v)
    body = f"{js_round(a):,}" if a >= 100 else to_fixed(a, 0 if a >= 10 else 1)
    return f"{sign}{body}%"


def times(v: float) -> str:
    """The page's multiple: "6.73×", "12.4×"."""
    return (to_fixed(v, 1) if v >= 10 else to_fixed(v, 2)) + "×"


def summary_times(v: float) -> str:
    """The summaries' multiple: "2.7×", "12×"."""
    return (to_fixed(v, 0) if v >= 10 else to_fixed(v, 1)) + "×"


def money(v: float) -> str:
    """The page's money: "$67,310"."""
    n = js_round(v)
    return ("-" if n < 0 else "") + f"${abs(n):,}"


def share(v: float | None) -> str:
    """The page's share of starts: "77%", "8.5%"."""
    if v is None:
        return "-"
    return _group(to_fixed(v, 0 if v >= 10 else 1)) + "%"


def long_date(iso: str) -> str:
    """The page's date: "May 5, 2026"."""
    y, m, d = iso.split("-")
    return f"{MONTHS[int(m) - 1]} {int(d)}, {y}"
