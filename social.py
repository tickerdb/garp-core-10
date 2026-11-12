"""
GitHub's social preview for this repo: the README's results chart with the model's name above the key,
on the site's background. 1280x640, the chart spanning the full width in the middle 470px, because
GitHub's topic and search cards crop the image to about 2.6:1 around its centre while link previews
show all of it. The chart card's side edges sit just outside the image.

    python social.py          # from the published record (results/record.json, run readme.py first); writes assets/social-preview.png
"""
from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from pathlib import Path

import charts
import readme

HERE = Path(__file__).resolve().parent
W, H, CHART_H, BLEED = 1280, 640, 470, 1
BG = "#04030c"          # tickerdb.com's page background
NAME = "GARP Core 10"


def render(svg: str, png: Path) -> None:
    """Screenshot the chart on the homepage background with headless Chrome (CHROME overrides the path)."""
    chrome = os.environ.get("CHROME") or next(
        (c for c in (shutil.which("chrome"), shutil.which("google-chrome"), shutil.which("chromium"),
                     r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                     "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome") if c and Path(c).exists()), None)
    if not chrome:
        raise SystemExit("Chrome not found; set CHROME to its path.")
    with tempfile.TemporaryDirectory() as tmp:
        (Path(tmp) / "chart.svg").write_text(svg, encoding="utf-8")
        page = Path(tmp) / "page.html"
        page.write_text(
            "<!doctype html><html><head><meta charset='utf-8'><style>"
            f"html,body{{margin:0;width:{W}px;height:{H}px;overflow:hidden;background:{BG}}}"
            f"img{{position:absolute;left:{-BLEED}px;top:{(H - CHART_H) // 2}px}}"
            "</style></head><body><img src='chart.svg'></body></html>", encoding="utf-8")
        subprocess.run([chrome, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--force-device-scale-factor=1",
                        f"--window-size={W},{H}", "--virtual-time-budget=3000", f"--screenshot={png}", page.as_uri()],
                       check=True, capture_output=True)
    print(f"Wrote {png.relative_to(HERE)} ({png.stat().st_size // 1024} KB). Upload it in the repo's "
          "Settings > General > Social preview (GitHub has no API for it).")


def main() -> None:
    record = readme.load()
    bt = record["backtest"]
    with tempfile.TemporaryDirectory() as tmp:
        svg = Path(tmp) / "results.svg"
        charts.results(bt["equity"], bt["benchmark"], readme.START_CASH, svg, size=(W + 2 * BLEED, CHART_H), title=NAME)
        render(svg.read_text(encoding="utf-8"), HERE / "assets" / "social-preview.png")


if __name__ == "__main__":
    main()
