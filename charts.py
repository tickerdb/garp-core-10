"""
The README's images, in the model page's dot style: Oxanium headings, Inter text, JetBrains Mono figures,
dark windows with a violet glow. The fonts (SIL Open Font License) are embedded in each SVG, so
GitHub shows them as designed.

    python charts.py          # the static images: the two "Run in" buttons
    python readme.py          # every other image, from the published record (results/record.json)
"""
from __future__ import annotations

import base64
import math
from datetime import date
from pathlib import Path
from statistics import median

import fmt

HERE = Path(__file__).resolve().parent
ASSETS = HERE / "assets"

PAGE, CARD, LINE = "#0e0e0f", "#141415", "#262628"
INK, SOFT, BODY, MUTED = "#f1f1f1", "#b6b6be", "#9a9aa2", "#7b7b83"
# Gains green, losses red, as the model page's tables (owner, 2026-11-11); white for the model and
# purple for the benchmark in the charts.
BENCH, LOSS = "#704eff", "#8a7fc4"
UP, DOWN = "#00e676", "#ff224a"
HEAD = "Oxanium,system-ui,sans-serif"
SANS = "Inter,system-ui,-apple-system,Segoe UI,sans-serif"
MONO = "JetBrains Mono,ui-monospace,Menlo,Consolas,monospace"
BENCH_NAME = "S&P 500"


def _b64(path: Path) -> str:
    return base64.b64encode(path.read_bytes()).decode()


def _fonts(*names: str) -> str:
    files = {"Oxanium": "oxanium-latin.woff2", "Inter": "inter-latin.woff2", "JetBrains Mono": "jetbrains-mono-latin.woff2"}
    return "".join(
        f"@font-face{{font-family:'{n}';font-weight:100 900;"
        f"src:url(data:font/woff2;base64,{_b64(ASSETS / 'fonts' / files[n])}) format('woff2')}}"
        for n in names
    )


def _open(w: int, h: int, fonts: tuple[str, ...], css: str = "") -> list[str]:
    return [
        f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" viewBox="0 0 {w} {h}" width="{w}" height="{h}">',
        f"<style>{_fonts(*fonts)}{css}</style>",
        "<defs>"
        '<radialGradient id="glow" cx="50%" cy="100%" r="60%">'
        '<stop offset="0" stop-color="#2e1462" stop-opacity="0.45"/><stop offset="0.35" stop-color="#21103f" stop-opacity="0.3"/>'
        '<stop offset="1" stop-color="#050212" stop-opacity="0"/></radialGradient>'
        '<radialGradient id="topglow" cx="50%" cy="0%" r="70%">'
        '<stop offset="0" stop-color="#2e1462" stop-opacity="0.35"/><stop offset="1" stop-color="#050212" stop-opacity="0"/></radialGradient>'
        f'<clipPath id="frame"><rect width="{w}" height="{h}" rx="16"/></clipPath>'
        "</defs>",
    ]


def _window(w: int, h: int) -> list[str]:
    return [
        f'<rect x="0.5" y="0.5" width="{w - 1}" height="{h - 1}" rx="16" fill="{CARD}" stroke="{LINE}"/>',
    ]


CLAUDE = ("m19.6 66.5 19.7-11 .3-1-.3-.5h-1l-3.3-.2-11.2-.3L14 53l-9.5-.5-2.4-.5L0 49l.2-1.5 2-1.3 2.9.2 6.3.5 9.5.6 6.9.4L38 49.1h1.6l.2-.7-.5-.4-.4-.4L29 41l-10.6-7-5.6-4.1-3-2-1.5-2-.6-4.2 2.7-3 3.7.3.9.2 3.7 2.9 8 6.1L37 36l1.5 1.2.6-.4.1-.3-.7-1.1L33 25l-6-10.4-2.7-4.3-.7-2.6c-.3-1-.4-2-.4-3l3-4.2L28 0l4.2.6L33.8 2l2.6 6 4.1 9.3L47 29.9l2 3.8 1 3.4.3 1h.7v-.5l.5-7.2 1-8.7 1-11.2.3-3.2 1.6-3.8 3-2L61 2.6l2 2.9-.3 1.8-1.1 7.7L59 27.1l-1.5 8.2h.9l1-1.1 4.1-5.4 6.9-8.6 3-3.5L77 13l2.3-1.8h4.3l3.1 4.7-1.4 4.9-4.4 5.6-3.7 4.7-5.3 7.1-3.2 5.7.3.4h.7l12-2.6 6.4-1.1 7.6-1.3 3.5 1.6.4 1.6-1.4 3.4-8.2 2-9.6 2-14.3 3.3-.2.1.2.3 6.4.6 2.8.2h6.8l12.6 1 3.3 2 1.9 2.7-.3 2-5.1 2.6-6.8-1.6-16-3.8-5.4-1.3h-.8v.4l4.6 4.5 8.3 7.5L89 80.1l.5 2.4-1.3 2-1.4-.2-9.2-7-3.6-3-8-6.8h-.5v.7l1.8 2.7 9.8 14.7.5 4.5-.7 1.4-2.6 1-2.7-.6-5.8-8-6-9-4.7-8.2-.5.4-2.9 30.2-1.3 1.5-3 1.2-2.5-2-1.4-3 1.4-6.2 1.6-8 1.3-6.4 1.2-7.9.7-2.6v-.2H49L43 72l-9 12.3-7.2 7.6-1.7.7-3-1.5.3-2.8L24 86l10-12.8 6-7.9 4-4.6-.1-.5h-.3L17.2 77.4l-4.7.6-2-2 .2-3 1-1 8-5.5Z")
OPENAI = ("M22.282 9.821a5.985 5.985 0 0 0-.516-4.91 6.046 6.046 0 0 0-6.51-2.9A6.065 6.065 0 0 0 4.981 4.18a5.985 5.985 0 0 0-3.998 2.9 6.046 6.046 0 0 0 .743 7.097 5.98 5.98 0 0 0 .51 4.911 6.051 6.051 0 0 0 6.515 2.9A5.985 5.985 0 0 0 13.26 24a6.056 6.056 0 0 0 5.772-4.206 5.99 5.99 0 0 0 3.997-2.9 6.056 6.056 0 0 0-.747-7.073zM13.26 22.43a4.476 4.476 0 0 1-2.876-1.04l.141-.081 4.779-2.758a.795.795 0 0 0 .392-.681v-6.737l2.02 1.168a.071.071 0 0 1 .038.052v5.583a4.504 4.504 0 0 1-4.494 4.494zM3.6 18.304a4.47 4.47 0 0 1-.535-3.014l.142.085 4.783 2.759a.771.771 0 0 0 .78 0l5.843-3.369v2.332a.08.08 0 0 1-.033.062L9.74 19.95a4.5 4.5 0 0 1-6.14-1.646zM2.34 7.896a4.485 4.485 0 0 1 2.366-1.973V11.6a.766.766 0 0 0 .388.676l5.815 3.355-2.02 1.168a.076.076 0 0 1-.071 0l-4.83-2.786A4.504 4.504 0 0 1 2.34 7.872zm16.597 3.855l-5.833-3.387L15.119 7.2a.076.076 0 0 1 .071 0l4.83 2.791a4.494 4.494 0 0 1-.676 8.105v-5.678a.79.79 0 0 0-.407-.667zm2.01-3.023l-.141-.085-4.774-2.782a.776.776 0 0 0-.785 0L9.409 9.23V6.897a.066.066 0 0 1 .028-.061l4.83-2.787a4.5 4.5 0 0 1 6.68 4.66zm-12.64 4.135l-2.02-1.164a.08.08 0 0 1-.038-.057V6.075a4.5 4.5 0 0 1 7.375-3.453l-.142.08L8.704 5.46a.795.795 0 0 0-.393.681zm1.097-2.365l2.602-1.5 2.607 1.5v2.999l-2.597 1.5-2.607-1.5z")


def button(path: Path, label: str, light: bool) -> None:
    """The site's chamfered button: light for the main action, dark for the other."""
    W, H, C = 22 + 18 + 10 + int(len(label) * 8.45) + 22, 46, 9
    shape = f"M0 0H{W - C}L{W} {C}V{H}H{C}L0 {H - C}Z"
    bg, fg = (INK, PAGE) if light else ("#1b1824", INK)
    icon = (f'<g transform="translate(22 14) scale(0.18)"><path fill="#d97757" d="{CLAUDE}"/></g>' if "Claude" in label
            else f'<g transform="translate(22 14) scale(0.75)"><path fill="{fg}" d="{OPENAI}"/></g>')
    out = _open(W, H, ("JetBrains Mono",)) + [
        f'<path d="{shape}" fill="{bg}"/>', icon,
        f'<text x="50" y="28.5" font-family="{MONO}" font-size="14" font-weight="500" fill="{fg}">{label}</text>',
        "</svg>",
    ]
    path.write_text("\n".join(out), encoding="utf-8")


def _esc(text: str) -> str:
    return text.replace("&", "&amp;")


def _legend(x: float, y: float, size: int = 11) -> str:
    """model in white, the S&P 500 in purple, each with a dot."""
    return (f'<g font-family="{MONO}" font-size="{size}">'
            f'<circle cx="{x + 3.5}" cy="{y - 4}" r="3.5" fill="{INK}"/>'
            f'<text x="{x + 12}" y="{y}" fill="{INK}">model</text>'
            f'<circle cx="{x + 70.5}" cy="{y - 4}" r="3.5" fill="{BENCH}"/>'
            f'<text x="{x + 79}" y="{y}" fill="{BENCH}">{_esc(BENCH_NAME)}</text></g>')

# ---- the model page's dots (tickerdb.com, 2026-11-11) -------------------------------------------
# Rounded squares, as the TickerDB logo, on a 3px grid; the fields fade over 42px from the line down
# (smaller and dimmer toward the floor); the benchmark line's dots carry a dark outline so they stand
# out over the field. src/lib/dot-shape.ts on the site holds the same numbers.
GRID = 3
FADE_PX = 42
LINE_R = 1.45
HALO = "#0a0912"


def _sq(cx: float, cy: float, r: float, extra: str = "") -> str:
    """One dot: a square about the circle's area, on whole pixels, its corners rounded from 4px up."""
    side = max(1, round(r * 1.8))
    x, y = round(cx - side / 2), round(cy - side / 2)
    rx = f' rx="{side * 0.3:.1f}"' if side >= 4 else ""
    return f'<rect x="{x}" y="{y}" width="{side}" height="{side}"{rx}{extra}/>'


def _fade_r(f: float) -> float:
    return 0.45 + 0.65 * f


def _fade_a(level: int, levels: int = 12) -> float:
    return 0.16 + 0.84 * ((level + 0.5) / levels) ** 0.7


def _dots(values: list[float], Y, right: float, base_y: float, color: str = INK, x0: float = 4,
          pitch: int = GRID) -> str:
    """The model page's dot field: per column, dots from the baseline to the value, largest and
    brightest at the value and fading toward the baseline. Columns for values below 0 hang down from
    the baseline at 0.55 of their opacity, like a losing year."""
    n = len(values)
    levels: dict[tuple[int, bool], list[str]] = {}
    for c in range(int(right / pitch) + 1):
        x = c * pitch
        i = min(n - 1, round(x / right * (n - 1)))
        top = Y(values[i])
        sign = 1 if top <= base_y else -1
        y = base_y
        while (y >= top - 0.5) if sign > 0 else (y <= top + 0.5):
            f = 2.718281828 ** (-abs(y - top) / FADE_PX)
            lvl = min(11, int(f * 12))
            levels.setdefault((lvl, values[i] < 0), []).append(_sq(x + x0, y, _fade_r(f)))
            y -= sign * pitch
    return (f'<g fill="{color}" shape-rendering="crispEdges">'
            + "".join(f'<g fill-opacity="{_fade_a(l) * (0.55 if neg else 1):.2f}">{"".join(c)}</g>'
                      for (l, neg), c in sorted(levels.items()))
            + "</g>")


def _dot_line(values: list[float], Y, right: float, color: str = BENCH, x0: float = 4) -> str:
    """The benchmark as a line of square dots with a dark outline; dots for values below 0 at 0.55."""
    n = len(values)
    dots = []
    for c in range(int(right / (GRID / 2)) + 1):
        x = c * GRID / 2
        i = min(n - 1, round(x / right * (n - 1)))
        dots.append(_sq(x + x0, Y(values[i]), LINE_R, ' fill-opacity="0.55"' if values[i] < 0 else ""))
    return (f'<g fill="{color}" stroke="{HALO}" stroke-width="2" paint-order="stroke" stroke-linejoin="round">'
            f'{"".join(dots)}</g>')


def _solid_line(values: list[float], Y, right: float, color: str = BENCH, x0: float = 4) -> str:
    """The benchmark as a solid 2px line over a dark underlay (the site's rolling-starts chart)."""
    n = len(values)
    pts = " ".join(f"{i / (n - 1) * right + x0:.1f},{Y(v):.1f}" for i, v in enumerate(values))
    return (f'<polyline points="{pts}" fill="none" stroke="{HALO}" stroke-width="4" stroke-linejoin="round" stroke-linecap="round"/>'
            f'<polyline points="{pts}" fill="none" stroke="{color}" stroke-width="2" stroke-linejoin="round" stroke-linecap="round"/>')


def _spark_field(vals: list[float], x: float, y: float, w: float, h: float, color: str) -> str:
    """The Stats card's charts as the page's: a dot field in the box, its line near the top."""
    n = len(vals)
    lo, hi = min(vals), max(vals)
    span = (hi - lo) or 1
    Y = lambda v: y + h - 2 - (v - lo) / span * (h - 8)
    xs = int(w / GRID) + 1
    pick = [vals[round(c / (xs - 1) * (n - 1))] for c in range(xs)]
    return _dots(pick, Y, w, y + h - 1, color, x0=x, pitch=GRID).replace("<g ", "<g ", 1)



def _label(x: float, y: float, text: str, anchor: str = "start") -> str:
    """A small uppercase label."""
    return (f'<text x="{x}" y="{y}" text-anchor="{anchor}" font-family="{MONO}" font-size="11" letter-spacing="0.9" '
            f'fill="{MUTED}">{_esc(text.upper())}</text>')


def _pct(p: float) -> str:
    """A figure in percent, as the model page writes it (fmt.signed_pct): whole percents from 10% up
    ("+37%", "+141%"), one decimal under 10% ("+6.6%", "-6.3%")."""
    return fmt.signed_pct(p)


def _pct0(v: float) -> str:
    """An axis label: 0% unsigned, others signed whole percents."""
    p = round(v * 100)
    return "0%" if p == 0 else f"{p:+d}%"


def _nice_step(span: float, ticks: int = 5) -> float:
    """A round step that splits span into about `ticks` parts: 1, 2, 2.5 or 5 times a power of ten."""
    raw = span / ticks
    p = 10 ** math.floor(math.log10(raw))
    return next(m * p for m in (1, 2, 2.5, 5, 10) if m * p >= raw)


def _field(values: list[float], X, Y, right: float, base_y: float, pitch: int = 6) -> str:
    """The model page's dot field: per column, dots from the baseline to the value, largest and
    brightest at the value's edge and fading toward the baseline. Columns for values below 0 hang
    down from the baseline at 0.55 of their opacity, like a losing year in the yearly ROI chart."""
    n = len(values)
    levels: dict[tuple[int, bool], list[str]] = {}
    for c in range(int(right / pitch) + 1):
        x = c * pitch
        i = min(n - 1, round(x / right * (n - 1)))
        top = Y(values[i])
        sign = 1 if top <= base_y else -1          # values below the baseline hang down from it
        y = base_y
        while (y >= top - 0.5) if sign > 0 else (y <= top + 0.5):
            f = 2.718281828 ** (-abs(y - top) / pitch / 7)
            lvl = min(11, int(f * 12))
            r = 0.55 + 1.55 * f
            levels.setdefault((lvl, values[i] < 0), []).append(f'<circle cx="{x + 4:.1f}" cy="{y:.1f}" r="{r:.2f}"/>')
            y -= sign * pitch
    return "".join(f'<g fill="{INK}" fill-opacity="{(0.1 + 0.9 * ((l + 0.5) / 12)) * (0.55 if neg else 1):.2f}">{"".join(c)}</g>'
                   for (l, neg), c in sorted(levels.items()))


def _line(values: list[float], Y, right: float, color: str = BENCH) -> str:
    """A line of dots; dots for values below 0 at 0.55 opacity."""
    n = len(values)
    dots = []
    for c in range(int(right / 3) + 1):
        x = c * 3
        i = min(n - 1, round(x / right * (n - 1)))
        op = ' fill-opacity="0.55"' if values[i] < 0 else ""
        dots.append(f'<circle cx="{x + 4:.1f}" cy="{Y(values[i]):.1f}" r="1.7"{op}/>')
    return f'<g fill="{color}">{"".join(dots)}</g>'


def _year_ticks(dates: list[str]) -> list[tuple[int, str]]:
    years = sorted({d[:4] for d in dates})[1:]
    return [(next(i for i, d in enumerate(dates) if d[:4] == y), y) for y in years]


def results(model: list[tuple[str, float]], bench: list[tuple[str, float]], start_cash: int, path: Path,
            size: tuple[int, int] = (960, 420), title: str | None = None) -> None:
    """The model page's results chart: the model's equity as a field of dots, largest and brightest at
    the top edge and fading below; the S&P 500 as a line of purple dots over it."""
    # social.py draws the GitHub social preview with this: a wider size, the model's name above the
    # key, and no fade-in (a screenshot would catch it half drawn).
    (W, H), PX = size, 28
    LEG = 47 if title else 38
    TOP, BOT, RIGHT = LEG + 24, H - 58, W - 108         # chart box; the balance scale sits right of it
    hi = max(max(v for _, v in model), max(v for _, v in bench)) * start_cash * 1.04
    step = int(_nice_step(hi))
    hi = (int(hi // step) + 1) * step
    n = len(model)
    X = lambda i: i / (n - 1) * RIGHT
    Y = lambda c: BOT - c / hi * (BOT - TOP)
    ticks = _year_ticks([d for d, _ in model])
    bmap = dict(bench)
    out = _open(W, H, ("JetBrains Mono", "Oxanium") if title else ("JetBrains Mono",),
                "" if title else ".f{opacity:0;animation:f 1.4s ease-out .1s forwards}@keyframes f{to{opacity:1}}")
    out += _window(W, H) + ([f'<text x="{PX}" y="28" font-family="{HEAD}" font-size="18" font-weight="500" fill="{INK}">{title}</text>']
                            if title else []) + [
        _legend(PX, LEG),
        f'<g font-family="{MONO}" font-size="11" fill="{MUTED}">'
        + "".join(f'<text x="{W - PX}" y="{Y(c) + 4:.1f}" text-anchor="end">${c:,.0f}</text>' for c in range(0, hi + 1, step))
        + "</g>",
        f'<g class="f">{_dots([v * start_cash for _, v in model], Y, RIGHT, BOT)}'
        f'{_dot_line([bmap[d] * start_cash for d, _ in model], Y, RIGHT)}</g>',
        f'<g font-family="{MONO}" font-size="11" fill="{MUTED}" text-anchor="middle">'
        + "".join(f'<text x="{X(i) + 4:.1f}" y="{BOT + 24}">{y}</text>' for i, y in ticks) + "</g>",
        "</svg>",
    ]
    path.write_text(chr(10).join(out), encoding="utf-8")


def _spark(vals: list[float], x: float, y: float, w: float, h: float, color: str, gid: str) -> str:
    """A dotted sparkline: one dot per column on the line, and fading dust below it."""
    step = 5
    n = int(w / step) + 1
    v = [vals[round(i / (n - 1) * (len(vals) - 1))] for i in range(n)]
    lo, hi = min(v), max(v)
    span = (hi - lo) or 1
    line, dust = [], []
    for i, val in enumerate(v):
        xx = x + i * step
        yy = y + h - 3 - (val - lo) / span * (h - 6)
        line.append(f'<circle cx="{xx:.1f}" cy="{yy:.1f}" r="1.7"/>')
        k, z = 1, yy + step
        while z <= y + h:
            o = max(0.08, 0.5 * 2.718281828 ** (-k / 3))
            dust.append(f'<circle cx="{xx:.1f}" cy="{z:.1f}" r="0.9" fill-opacity="{o:.2f}"/>')
            k += 1
            z += step
    return f'<g fill="{color}">{"".join(dust)}{"".join(line)}</g>'


def stats(model: list[tuple[str, float]], bench: list[tuple[str, float]], start_cash: int,
          m: dict, b: dict, path: Path) -> None:
    """The model page's Stats card: the model's and the benchmark's multiples over their dot fields,
    side by side 2px apart, then balance, ROI, CAGR and max drawdown, the model's figure green where it
    beats the benchmark and red where it trails (the page's table)."""
    W, H, PX = 960, 330, 28
    times = fmt.times
    big = [("model", times(m["multiple"]), INK, [math.log(v) for _, v in model]),
           (BENCH_NAME, times(b["multiple"]), BENCH, [math.log(v) for _, v in bench])]
    out = _open(W, H, ("Oxanium", "JetBrains Mono")) + _window(W, H)
    col = (W - 2 * PX - 2) / 2
    for k, (label, value, color, series) in enumerate(big):
        x = PX + k * (col + 2)
        out += [_spark_field(series, x, 58, col, 150, color),
                _label(x, 40, label),
                f'<text x="{x}" y="96" font-family="{HEAD}" font-size="50" font-weight="500" fill="{color}">{value}</text>']
    pair = [("balance", fmt.money(m['multiple'] * start_cash), fmt.money(b['multiple'] * start_cash), m["multiple"] > b["multiple"]),
            ("roi", _pct(m['roi'] * 100), _pct(b['roi'] * 100), m["roi"] > b["roi"]),
            ("CAGR", _pct(m['cagr'] * 100), _pct(b['cagr'] * 100), m["cagr"] > b["cagr"]),
            ("max drawdown", _pct(m['max_drawdown'] * 100), _pct(b['max_drawdown'] * 100), m["max_drawdown"] > b["max_drawdown"])]
    col = (W - 2 * PX) / 4
    for k, (label, mv, bv, good) in enumerate(pair):
        x = PX + k * col
        out += [_label(x, 256, label),
                f'<text x="{x}" y="290" font-family="{MONO}" font-size="18" fill="{UP if good else DOWN}">{mv}'
                f'<tspan dx="10" font-size="13" fill="{BENCH}">{bv}</tspan></text>']
    out.append("</svg>")
    path.write_text(chr(10).join(out), encoding="utf-8")


def edge(model: list[tuple[str, float]], bench: list[tuple[str, float]], m: dict, b: dict, path: Path) -> None:
    """The model page's Edge card: the model's balance over the benchmark's, "model beats X by" and the
    multiple in green (red when it trails), its dot field across the card, then peak, low, time ahead
    and edge a year (lib/model-summaries.ts edgeFigures on the site)."""
    W, H, PX = 960, 330, 28
    bmap = dict(bench)
    series = [(d, v / bmap[d]) for d, v in model if d in bmap and bmap[d] > 0]
    end = series[-1][1]
    peak = max(series, key=lambda p: p[1])
    low = min(series, key=lambda p: p[1])
    rest = series[1:]
    ahead = sum(v > 1 for _, v in rest) / len(rest) * 100
    yearly = ((1 + m["cagr"]) / (1 + b["cagr"]) - 1) * 100
    times = fmt.times
    tone = UP if end >= 1 else DOWN
    out = _open(W, H, ("Oxanium", "JetBrains Mono")) + _window(W, H)
    out += [_spark_field([v for _, v in series], PX, 58, W - 2 * PX, 150, tone),
            f'<text x="{PX}" y="40" font-family="{MONO}" font-size="11" letter-spacing="0.9" fill="{tone}">'
            f'{_esc((("model beats " + BENCH_NAME + " by") if end >= 1 else ("model trails " + BENCH_NAME + " at")).upper())}</text>',
            f'<text x="{PX}" y="96" font-family="{HEAD}" font-size="50" font-weight="500" fill="{tone}">{times(end)}</text>']
    figs = [("peak", times(peak[1]), peak[1] > 1), ("low", times(low[1]), low[1] >= 1),
            ("time ahead", f"{fmt.js_round(ahead)}% of days", ahead >= 50), ("edge a year", _pct(yearly), yearly > 0)]
    col = (W - 2 * PX) / 4
    for k, (label, value, good) in enumerate(figs):
        x = PX + k * col
        out += [_label(x, 256, label),
                f'<text x="{x}" y="290" font-family="{MONO}" font-size="18" fill="{UP if good else DOWN}">{value}</text>']
    out.append("</svg>")
    path.write_text(chr(10).join(out), encoding="utf-8")


def tape(trades: list[dict], path: Path, rows: int = 12, this_year: int | None = None) -> None:
    """The model page's trade tape, newest first: stock, entry, exit, ROI. Gains are white, losses dim
    purple; an open holding is marked live. Side triangles (long white, short purple) appear only when
    the trades include both sides; a long-only model's tape has none. A trade without "side" is long."""
    this_year = this_year or date.today().year     # dates of this year print without it
    marked = len({t.get("side", "long") for t in trades}) > 1

    def fmt(iso: str | None) -> str:
        if not iso:
            return ""
        d = date.fromisoformat(iso)
        return d.strftime("%b %d").lower() + ("" if d.year == this_year else f" {d.year}")

    order = sorted(range(len(trades)), key=lambda k: (trades[k]["exit_date"] or "9999", k))
    recent = [trades[k] for k in reversed(order)][:rows]
    W, PX, RH, HEAD_Y = 960, 28, 34, 46
    H = HEAD_Y + RH * len(recent) + 16
    quarter = (W - 2 * PX) / 4                 # four even columns, all left-aligned, like the page
    c0, c1, c2, c3 = PX, PX + quarter, PX + 2 * quarter, PX + 3 * quarter
    out = _open(W, H, ("JetBrains Mono",)) + _window(W, H) + [
        f'<g font-family="{MONO}" font-size="11" letter-spacing="0.9" fill="{MUTED}">'
        f'<text x="{c0}" y="{HEAD_Y - 14}">STOCK</text><text x="{c1}" y="{HEAD_Y - 14}">ENTRY</text>'
        f'<text x="{c2}" y="{HEAD_Y - 14}">EXIT</text><text x="{c3}" y="{HEAD_Y - 14}">ROI</text></g>',
        f'<g font-family="{MONO}" font-size="14">',
    ]
    for k, t in enumerate(recent):
        cy = HEAD_Y + RH * k + 22
        live = t["exit_date"] is None
        r = t["return_pct"]
        if live:
            out.append(f'<rect x="1" y="{cy - 22}" width="{W - 2}" height="{RH}" fill="{BENCH}" fill-opacity="0.10"/>')
        ret = "" if r is None else _pct(float(r)) + (" live" if live else "")
        tone = f'fill="{UP}" font-weight="600"' if float(r or 0) >= 0 else f'fill="{DOWN}"'
        mark, tx = "", c0
        if marked:
            is_long = t.get("side", "long") == "long"
            tri = (f"M{c0 + 5} {cy - 11} L{c0 + 10} {cy - 2} L{c0} {cy - 2}Z" if is_long
                   else f"M{c0} {cy - 11} L{c0 + 10} {cy - 11} L{c0 + 5} {cy - 2}Z")
            mark, tx = f'<path d="{tri}" fill="{INK if is_long else BENCH}"/>', c0 + 22
        out.append(mark +
                   f'<text x="{tx}" y="{cy}" fill="{INK}">{_esc(t["ticker"])}</text>'
                   f'<text x="{c1}" y="{cy}" fill="{MUTED}">{fmt(t["entry_date"])}</text>'
                   f'<text x="{c2}" y="{cy}" fill="{INK}">{fmt(t["exit_date"])}</text>'
                   f'<text x="{c3}" y="{cy}" {tone}>{ret}</text>')
    out += ["</g>", "</svg>"]
    path.write_text(chr(10).join(out), encoding="utf-8")


def years(model: dict[str, float], bench: dict[str, float], path: Path) -> None:
    """The model page's Yearly ROI: per year a white dot column (model) beside a purple one (S&P 500),
    four dots wide, gains up from a dotted baseline and losses hanging below it; returns underneath."""
    rows = sorted(model)
    W, PX, STEP, UP_H = 960, 28, GRID, 150
    vmax = max(max(model.values()), max(bench.values()), 1e-9)
    vmin = min(min(model.values()), min(bench.values()), 0)
    down_h = max(STEP, -(-(-vmin / vmax * UP_H) // STEP) * STEP)
    base = 32 + UP_H
    H = int(base + down_h + 82)
    col_w = (W - 2 * PX) / len(rows)
    out = _open(W, H, ("JetBrains Mono",)) + _window(W, H)
    out.append(f'<g fill="{INK}" fill-opacity="0.18">' + "".join(
        _sq(xx, base + 3, 0.9) for xx in range(PX, W - PX, 6)) + "</g>")
    for k, y in enumerate(rows):
        cx = PX + col_w * (k + 0.5)
        for j, (val, color) in enumerate(((model[y], INK), (bench.get(y, 0.0), BENCH))):
            dots = max(1, round(abs(val) / vmax * UP_H / STEP))
            x0 = cx - 38 + j * 40
            g = []
            for q in range(dots):
                yy = base - 2 - q * STEP if val >= 0 else base + 8 + q * STEP
                for c in range(12):
                    g.append(_sq(x0 + c * STEP + 1.5, yy, 1.05))
            op = "" if val >= 0 else ' fill-opacity="0.55"'
            out.append(f'<g fill="{color}"{op} shape-rendering="crispEdges">{"".join(g)}</g>')
        ly = base + down_h + 26
        mv, bv = model[y] * 100, bench.get(y, 0.0) * 100
        out.append(f'<g font-family="{MONO}" text-anchor="middle">'
                   f'<text x="{cx:.1f}" y="{ly}" font-size="12" fill="{INK if k == len(rows) - 1 else MUTED}">&#8217;{y[2:]}</text>'
                   f'<text x="{cx:.1f}" y="{ly + 22}" font-size="13" {"font-weight=" + chr(34) + "600" + chr(34) if mv >= 0 else ""} fill="{UP if mv >= 0 else DOWN}">{_pct(mv)}</text>'
                   f'<text x="{cx:.1f}" y="{ly + 40}" font-size="12" fill="{BENCH}">{_pct(bv)}</text></g>')
    out.append("</svg>")
    path.write_text(chr(10).join(out), encoding="utf-8")


def rolling(starts: list[dict], end: str, path: Path, min_weeks: int = 104) -> None:
    """Rolling starts, in the results chart's style: for each weekly start date with at least two years
    to run, the model's CAGR from that start to the end as a field of dots, and the S&P 500's CAGR over
    the same weeks as a line of purple dots. The plot runs edge to edge; the percent labels sit small
    inside it at the right."""
    rs = [r for r in starts if r["weeks"] >= min_weeks]
    W, H, PX = 960, 420, 28
    TOP, BOT, RIGHT = 62, 362, W - 8          # columns at x + 4: edge to edge inside the window
    vals = [r["cagr"] for r in rs] + [r["SPY_cagr"] for r in rs]
    top, bot = max(0.0, max(vals)), min(0.0, min(vals))     # the dot field grows from 0%, like results' $0
    step = _nice_step((top - bot) * 1.04 or 0.1, 4)
    hi = (math.floor(top * 1.04 / step) + 1) * step if top > 0 else 0.0
    lo = math.floor(bot * 1.04 / step) * step
    n = len(rs)
    X = lambda i: i / (n - 1) * RIGHT
    Y = lambda v: BOT - (v - lo) / (hi - lo) * (BOT - TOP)
    ticks = _year_ticks([r["start"] for r in rs])
    levels = [lo + k * step for k in range(round((hi - lo) / step) + 1)]
    out = _open(W, H, ("JetBrains Mono",),
                ".f{opacity:0;animation:f 1.4s ease-out .1s forwards}@keyframes f{to{opacity:1}}")
    out += _window(W, H) + [
        _legend(PX, 38),
        _label(W - PX, 38, f"CAGR from each weekly start to {end}", "end"),
    ]
    if lo < 0:
        out.append(f'<g fill="{INK}" fill-opacity="0.18">' + "".join(
            _sq(xx + 4, Y(0), 0.9) for xx in range(0, int(RIGHT), 6)) + "</g>")
    out += [
        f'<g class="f">{_dots([r["cagr"] for r in rs], Y, RIGHT, Y(0))}{_solid_line([r["SPY_cagr"] for r in rs], Y, RIGHT)}</g>',
        f'<g font-family="{MONO}" font-size="11" fill="{MUTED}" text-anchor="middle">'
        + "".join(f'<text x="{X(i) + 4:.1f}" y="{BOT + 24}">{y}</text>' for i, y in ticks) + "</g>",
        # small percent labels inside the plot, over the dots, with a halo in the window's colour
        f'<g font-family="{MONO}" font-size="10" fill="{MUTED}" text-anchor="end" stroke="{CARD}" stroke-width="4" '
        f'paint-order="stroke">' + "".join(f'<text x="{W - 12}" y="{Y(v) - 5:.1f}">{_pct0(v)}</text>'
                                            for v in levels) + "</g>",
        "</svg>",
    ]
    path.write_text(chr(10).join(out), encoding="utf-8")


def windows(starts: list[dict], path: Path) -> None:
    """Fixed 1, 2 and 3-year returns from every weekly start, as dot histograms in the results chart's
    dot language: x is the return, bucketed on the 6px grid; each column is as tall as the number of
    starts that landed in its bucket, its top dot largest and brightest, fading to dust toward the
    dotted baseline. The model rises above the baseline in white; the S&P 500 hangs below it in
    purple. Returns below 0% are drawn at 0.55 opacity, like a losing year in the yearly ROI chart.
    The median's top dot is a little larger. The histograms use the full width on one shared x axis
    fitted to the lowest and highest return; the figures are in the README's table."""
    horizons = [(k, label) for k, label in (("1y", "1 year"), ("2y", "2 years"), ("3y", "3 years"))
                if any(r.get(k) is not None for r in starts)]
    data = {}
    for k, _ in horizons:
        rs = [r for r in starts if r.get(k) is not None]
        data[k] = (sorted(r[k] for r in rs), sorted(r[f"{k}_SPY"] for r in rs),
                   sum(r[k] > r[f"{k}_SPY"] for r in rs) / len(rs))
    allv = [v for m, b, _ in data.values() for v in m + b]
    span = (max(allv) - min(allv)) or 0.1            # one shared axis fitted to every return shown
    lo, hi = min(allv) - 0.02 * span, max(allv) + 0.02 * span
    step = _nice_step(hi - lo, 6)
    W, PX, PITCH, MAXD = 960, 28, 6, 9
    X0, X1 = PX + 4, W - PX - 4
    X = lambda v: X0 + (v - lo) / (hi - lo) * (X1 - X0)
    bucket = lambda v: round((X(v) - X0) / PITCH)
    TOP, BLOCK = 62, 156
    H = TOP + BLOCK * len(horizons) + 30
    out = _open(W, H, ("JetBrains Mono",)) + _window(W, H) + [
        _legend(PX, 38),
    ]
    for b, (k, label) in enumerate(horizons):
        m, s, beat = data[k]
        y0 = TOP + b * BLOCK
        base = y0 + 30 + MAXD * PITCH                 # model dots sit above it, the S&P 500's hang below
        out.append(_label(PX, y0 + 14, f"{label} from each start · {len(m)} starts · beat the {BENCH_NAME} in {beat:.0%}"))
        out.append(f'<g fill="{INK}" fill-opacity="0.18">' + "".join(
            _sq(xx, base + 3, 0.9) for xx in range(X0, X1 + 1, PITCH)) + "</g>")
        counts, losing = [], []
        for vals in (m, s):
            c: dict[int, int] = {}
            neg: dict[int, int] = {}
            for v in vals:
                c[bucket(v)] = c.get(bucket(v), 0) + 1
                neg[bucket(v)] = neg.get(bucket(v), 0) + (v < 0)
            counts.append(c)
            losing.append({col for col in c if neg[col] * 2 > c[col]})   # buckets of mostly sub-0% returns
        peak = max(max(c.values()) for c in counts)
        for j, (vals, color, c) in enumerate(((m, INK, counts[0]), (s, BENCH, counts[1]))):
            mid = bucket(median(vals))
            dots = []
            for col, n in sorted(c.items()):
                h = max(1, math.ceil(n / peak * MAXD))
                cx = X0 + col * PITCH
                for q in range(h):                    # q = 0 at the baseline, h - 1 at the top
                    f = 2.718281828 ** (-(h - 1 - q) / 2.2)
                    r = 0.7 + 1.5 * f
                    if q == h - 1 and col == mid:
                        r = 3.0
                    cy = base - 3 - q * PITCH if j == 0 else base + 9 + q * PITCH
                    dim = 0.55 if col in losing[j] else 1.0     # returns below 0%, like a losing year
                    dots.append(_sq(cx, cy, r, f' fill-opacity="{(0.18 + 0.82 * f) * dim:.2f}"'))
            if mid not in c:
                op = ' fill-opacity="0.55"' if median(vals) < 0 else ""
                dots.append(_sq(X0 + mid * PITCH, base - 3 if j == 0 else base + 9, 3, op))
            out.append(f'<g fill="{color}" shape-rendering="crispEdges">{"".join(dots)}</g>')
    first = math.ceil(lo / step - 1e-9) * step         # round steps inside the fitted range
    ticks = [first + k * step for k in range(int((hi - first) / step + 1e-9) + 1)]
    ay = TOP + BLOCK * len(horizons) + 10
    out.append(f'<g font-family="{MONO}" font-size="11" fill="{MUTED}" text-anchor="middle">'
               + "".join(f'<text x="{X(v):.1f}" y="{ay}">{_pct0(v)}</text>' for v in ticks) + "</g>")
    out.append("</svg>")
    path.write_text(chr(10).join(out), encoding="utf-8")


if __name__ == "__main__":
    button(ASSETS / "open-in-claude.svg", "Run in Claude", light=True)
    button(ASSETS / "open-in-chatgpt.svg", "Run in ChatGPT", light=False)
    print("wrote assets/open-in-claude.svg, assets/open-in-chatgpt.svg")
