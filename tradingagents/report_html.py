"""The report as one self-contained HTML page (#1419).

The page reads well in a browser, on a phone and in print. It loads nothing and
runs nothing: styles are inline, there is no script, and a Content-Security-Policy
forbids any fetch. Report text is rendered as CommonMark with raw HTML and images
off, so nothing a model wrote can inject markup or load a remote asset.
"""

import csv
from datetime import datetime
from html import escape
from importlib.resources import files
from pathlib import Path
from tradingagents.dataflows.symbols import safe_ticker_component
import csv

from markdown_it import MarkdownIt

from tradingagents.agents.rating import run_rating
from tradingagents.reporting import analyst_names

# Ratings by direction, so the page can show which way the call leans.
_TONE = {"Buy": "up", "Overweight": "up", "Hold": "level", "Underweight": "down", "Sell": "down"}

# The Tauric Research logo as published (tauric.ai/brand/tauric-logo.svg), drawn
# in the page so it loads nothing.
_LOGO = files("tradingagents").joinpath("assets/tauric-logo.svg").read_text(encoding="utf-8").strip()
_COMPANY = "https://tauric.ai"
_ORG = "https://github.com/TauricResearch"
_PROJECT = f"{_ORG}/TradingAgents"

_CSS = """
:root {
  --paper: #fbfbfa; --ink: #1c2126; --muted: #5d6670; --rule: #e2e5e8; --wash: #f2f4f5;
  --accent: #087a59; --up: #087a59; --down: #b4372f; --level: #5d6670; --edge: #d3d8dc; --mark: #878f97;
  --serif: Charter, "Bitstream Charter", "Sitka Text", Cambria, Georgia, serif;
  --sans: system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
  color-scheme: light dark;
}
@media (prefers-color-scheme: dark) {
  :root {
    --paper: #131a1f; --ink: #e4e8eb; --muted: #9aa6af; --rule: #263239; --wash: #1a242a;
    --accent: #14c290; --up: #14c290; --down: #ef6f63; --level: #9aa6af; --edge: #3d4c55; --mark: #66737c;
  }
}
@media (prefers-color-scheme: dark) {
  .masthead .logo [stroke="#363636"] { stroke: var(--muted); }
}
* { box-sizing: border-box; }
html { -webkit-text-size-adjust: 100%; }
body {
  margin: 0; background: var(--paper); color: var(--ink);
  font: 17px/1.62 var(--serif); font-kerning: normal;
}
.page { max-width: 46rem; margin: 0 auto; padding: 3.5rem 1.5rem 6rem; }
main h2, main h3 { scroll-margin-top: 1rem; }
a { color: var(--accent); text-underline-offset: 0.15em; }
h1, h2, h3, h4 { text-wrap: balance; }
a:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }

.masthead { padding-bottom: 1.75rem; border-bottom: 1px solid var(--rule); }
/* The logo leads at the top left, where readers look for it, 24px tall (the usual
   on-screen floor for a wordmark) with at least its height clear below. */
.masthead .logo { display: block; width: fit-content; margin: 0 0 2.25rem; }
.masthead .logo svg { display: block; height: 1.5rem; width: auto; }
.masthead h1 {
  margin: 0; font: 600 2.6rem/1.1 var(--sans); letter-spacing: -0.02em;
  display: flex; flex-wrap: wrap; align-items: baseline; gap: 0.2em 0.5em;
}
.masthead .rating { font-weight: 500; }
.rating.up { color: var(--up); } .rating.down { color: var(--down); } .rating.level { color: var(--level); }
.rating.review { color: var(--muted); font-style: italic; }
.masthead .date { margin: 0.55rem 0 1.5rem; font: 1rem/1.4 var(--sans); color: var(--muted); }
.run { margin: 0; display: grid; grid-template-columns: max-content 1fr; gap: 0.45rem 1.25rem;
  font: 0.85rem/1.5 var(--sans); }
.run > div { display: contents; }
.run dt { color: var(--muted); }
.run dd { margin: 0; overflow-wrap: anywhere; }
.run .note dd { color: var(--down); }
.field { display: inline-block; margin: 0 0.15rem 0.15rem 0; padding: 0 0.4rem; border: 1px solid var(--edge);
  border-radius: 4px; background: var(--wash); font: 0.8rem/1.6 ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; }
.run .group { display: inline-block; margin-right: 0.9rem; white-space: nowrap; }
.run .group > .name { color: var(--muted); margin-right: 0.3rem; }
.run .then { color: var(--muted); margin: 0 0.2rem; }
.decision-visual { margin-top: 1.5rem; padding: 1rem; border: 1px solid var(--rule); border-radius: 8px; background: var(--wash); }
.decision-visual-title { margin: 0 0 0.7rem; color: var(--muted); font: 600 0.78rem/1.4 var(--sans); text-transform: uppercase; letter-spacing: 0.08em; }
.rating-spectrum { display: grid; grid-template-columns: repeat(5, minmax(0, 1fr)); gap: 0.35rem; }
.rating-step { min-height: 2.1rem; display: grid; place-items: center; padding: 0.35rem 0.2rem; border-radius: 4px; background: var(--paper); color: var(--muted); font: 600 0.72rem/1.2 var(--sans); text-align: center; }
.rating-step.down { border-bottom: 3px solid var(--down); }
.rating-step.level { border-bottom: 3px solid var(--level); }
.rating-step.up { border-bottom: 3px solid var(--up); }
.rating-step.active { outline: 2px solid var(--ink); outline-offset: 1px; color: var(--ink); }
.reader-summary { margin: 1.5rem 0 0; display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: .6rem; font: .82rem/1.45 var(--sans); }
.summary-card { min-width: 0; padding: .8rem; border: 1px solid var(--rule); border-radius: 6px; background: var(--wash); }
.summary-card strong { display:block; margin-top:.25rem; font-size:1.05rem; font-variant-numeric:tabular-nums; }
.summary-card small { display:block; color:var(--muted); margin-top:.25rem; }
.report-guide { margin: 1.5rem 0; padding: 1rem; border-left: 3px solid var(--accent); background: var(--wash); font: .9rem/1.55 var(--sans); }
.report-guide h2 { margin:0 0 .45rem; font-size:1rem; }
.report-guide p { margin:.35rem 0; }
.market-chart { margin: 2rem 0; padding: 1rem; border: 1px solid var(--rule); border-radius: 8px; background: var(--wash); break-inside: avoid; }
.market-chart h2 { margin:0 0 .2rem; font:600 1.15rem/1.35 var(--sans); }
.market-chart p { margin:.4rem 0; color:var(--muted); font: .82rem/1.5 var(--sans); }
.market-chart svg { display:block; width:100%; height:auto; overflow:visible; }
.market-chart .gridline { stroke:var(--edge); stroke-dasharray:3 5; }
.market-chart .axis-label { fill:var(--muted); font:12px var(--sans); }
.market-chart .series-close { fill:none; stroke:#087a59; stroke-width:2.8; }
.market-chart .series-sma50 { fill:none; stroke:#c07a12; stroke-width:2; }
.market-chart .series-sma200 { fill:none; stroke:#6853a6; stroke-width:2; }
.chart-legend { display:flex; flex-wrap:wrap; gap:.85rem; margin-top:.5rem; font: .78rem var(--sans); color:var(--muted); }
.chart-legend span { display:flex; align-items:center; gap:.4rem; }
.chart-legend i { display:inline-block; width:1.2rem; border-top:2px solid; }
.chart-legend .legend-close { color:#087a59; } .chart-legend .legend-sma50 { color:#c07a12; } .chart-legend .legend-sma200 { color:#6853a6; }

/* The sections: listed under the header on narrow screens. On wide ones, a
   quiet rail centred on the left edge (numerals for the sections, short bars
   for their agents) that opens into the full list when pointed at or focused. */
.contents { margin: 2.25rem 0 0; font: 0.9rem/1.45 var(--sans); }
.contents ul { margin: 0; padding: 0; list-style: none; }
.contents > ul > li { margin: 0 0 0.75rem; }
.contents ul ul { margin-top: 0.2rem; padding-left: 1.6rem; font-size: 0.85rem; }
.contents ul ul li { margin: 0.1rem 0; }
.contents a { display: flex; align-items: center; gap: 0.6rem; color: var(--muted); text-decoration: none; }
.contents > ul > li > a { color: var(--ink); }
.contents .num { min-width: 1.6rem; color: var(--muted); font-variant-numeric: tabular-nums; }
.contents .bar { display: none; }
.contents a:hover .label, .contents a:focus-visible .label { color: var(--accent); text-decoration: underline; }
.to-top { position: fixed; right: 1rem; bottom: calc(1rem + env(safe-area-inset-bottom));
  padding: 0.25rem 0.6rem; border: 1px solid var(--edge); border-radius: 4px; background: var(--paper);
  color: var(--muted); font: 0.8rem/1.4 var(--sans); text-decoration: none; }

@media (min-width: 60rem) {
  .contents { position: fixed; left: 1rem; top: 50%; transform: translateY(-50%); z-index: 1;
    max-height: 86vh; overflow-y: auto; overscroll-behavior: contain; margin: 0;
    padding: 0.7rem 0.9rem; border: 1px solid transparent; border-radius: 6px;
    transition: background-color 0.15s, border-color 0.15s, box-shadow 0.15s; }
  .contents > ul > li { margin: 0 0 0.35rem; }
  .contents ul ul { margin-top: 0; padding-left: 0; }
  .contents ul ul li { margin: 0; }
  /* Marks reach 3:1 contrast and rows 24px, the WCAG 2.2 floors for a control's
     visual cue and its pointer target. */
  .contents a { min-height: 1.5rem; }
  .contents .num { min-width: 1.4rem; }
  .contents .bar { display: block; flex: none; width: 1.25rem; height: 2px; margin-left: 0.2rem;
    border-radius: 1px; background: var(--mark); }
  .contents .label { max-width: 0; opacity: 0; overflow: hidden; white-space: nowrap;
    transition: opacity 0.15s, max-width 0.2s; }
  .contents:hover, .contents:focus-within { background: var(--paper); border-color: var(--rule);
    box-shadow: 0 6px 24px rgb(0 0 0 / 0.08); }
  .contents:hover .label, .contents:focus-within .label { max-width: 18rem; opacity: 1; }
  .contents a:hover .bar, .contents a:focus-visible .bar { background: var(--accent); }
  .to-top { display: none; }
}
@media (prefers-reduced-motion: reduce) {
  .contents, .contents .label { transition: none; }
}

/* The maker's credit: one quiet line at the foot. */
.credit { margin-top: 4.5rem; padding-top: 1.25rem; border-top: 1px solid var(--rule);
  color: var(--muted); font: 0.8rem/1.4 var(--sans); }
.credit a { color: inherit; text-decoration: none; }
.credit a.brand { color: var(--accent); }
.credit a:hover, .credit a:focus-visible { text-decoration: underline; }

/* Three levels of separation: the five groups, the agents within a group, and
   breaks an agent draws inside its own text. */
main h2 {
  margin: 4.5rem 0 0.25rem; padding-top: 1.5rem; border-top: 2px solid var(--ink);
  font: 600 1.45rem/1.3 var(--sans); letter-spacing: -0.01em;
}
main section:first-child h2 { margin-top: 3rem; }
main h3 { margin: 2.75rem 0 0.75rem; padding-top: 1.1rem; border-top: 1px solid var(--rule);
  font: 600 1.15rem/1.35 var(--sans); color: var(--accent); }
main h2 + h3 { margin-top: 1.25rem; padding-top: 0; border-top: 0; }
main h4, main h5, main h6 { margin: 1.75rem 0 0.5rem; font: 600 1rem/1.4 var(--sans); }
main h5, main h6 { color: var(--muted); }
main p, main ul, main ol { margin: 0 0 1rem; }
main li { margin: 0.25rem 0; }
main strong { font-weight: 650; }
main blockquote { margin: 1.25rem 0; padding: 0.1rem 0 0.1rem 1rem; border-left: 3px solid var(--rule);
  color: var(--muted); }
main code { font: 0.88em/1.4 ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  background: var(--wash); padding: 0.1em 0.3em; border-radius: 3px; }
main pre { background: var(--wash); padding: 0.9rem 1rem; border-radius: 4px; overflow-x: auto; }
main pre code { background: none; padding: 0; }
main hr { width: 3rem; margin: 2rem auto; border: 0; border-top: 1px solid var(--rule); }

.table { overflow-x: auto; margin: 0 0 1.25rem; }
table { border-collapse: collapse; width: 100%; font: 0.86rem/1.45 var(--sans);
  font-variant-numeric: tabular-nums; }
th, td { padding: 0.45rem 0.7rem; text-align: left; vertical-align: top; border-bottom: 1px solid var(--rule); }
th { font-weight: 600; border-bottom-color: var(--muted); }
tbody tr:last-child td { border-bottom: 0; }

@media (max-width: 34rem) {
  body { font-size: 16px; }
  .page { padding: 2rem 1rem 3rem; }
  .masthead h1 { font-size: 2rem; }
  .masthead .logo svg { height: 1.25rem; }
  .run { grid-template-columns: 1fr; gap: 0 0; }
  .run dd { margin-bottom: 0.45rem; }
  .run .group { white-space: normal; }
  .reader-summary { grid-template-columns:1fr; }
}
@media print {
  :root { --paper: #fff; --ink: #000; --muted: #444; --rule: #bbb; --accent: #000; --wash: #f2f2f2;
    --edge: #bbb; --up: #087a59; --down: #b4372f; --level: #444; }
  body { font-size: 11pt; }
  .table { overflow: visible; }
  .page { max-width: none; padding: 0; }
  .contents, .to-top { display: none; }
  main h2 { break-before: page; border-top: 0; margin-top: 0; }
  main section:first-child h2 { break-before: auto; }
  main h3, main h4 { break-after: avoid; }
  a { color: inherit; text-decoration: none; }
  table { break-inside: avoid; }
}
"""


def _markdown() -> MarkdownIt:
    md = MarkdownIt("commonmark", {"html": False}).enable("table").disable("image")
    md.add_render_rule("table_open", lambda *a: '<div class="table"><table>\n')
    md.add_render_rule("table_close", lambda *a: "</table></div>\n")
    return md


def _render_agent_text(md: MarkdownIt, text: str) -> str:
    """An agent's text, its own headings placed below the agent's heading (h3)."""
    tokens = md.parse(text)
    for token in tokens:
        if token.type in ("heading_open", "heading_close"):
            token.tag = f"h{min(int(token.tag[1]) + 3, 6)}"
    return md.renderer.render(tokens, md.options, {})


# What each data category serves, as a reader would name it.
_CATEGORY = {
    "core_stock_apis": "Prices", "technical_indicators": "Indicators", "fundamental_data": "Fundamentals",
    "news_data": "News", "macro_data": "Macro", "prediction_markets": "Prediction markets",
}


def _fields(values) -> str:
    return " ".join(f'<span class="field">{escape(str(v))}</span>' for v in values)


def _chain(vendors: str) -> str:
    """A vendor chain in the order it is tried: ``a,b`` reads a, then b."""
    names = [v.strip() for v in str(vendors).split(",") if v.strip()]
    return ' <span class="then">\u2192</span> '.join(_fields([n]) for n in names)


def _group(name: str, values_html: str) -> str:
    return f'<span class="group"><span class="name">{escape(name)}</span>{values_html}</span>'


def _run_details(final_state: dict, settings: dict | None) -> list[tuple[str, str]]:
    """The run details as (label, value HTML); every value from the run is escaped."""
    details = [("Generated", escape(datetime.now().strftime("%Y-%m-%d %H:%M")))]
    if settings:
        s = settings.get
        for tier in ("deep", "quick"):
            provider = s(f"{tier}_think_provider") or s("llm_provider", "?")
            details.append((f"{tier.capitalize()} model", _fields([provider, s(f"{tier}_think_llm", "?")])))
        details.append(("Analysts", _fields(analyst_names(s("analysts")))))
        details.append(("Debate rounds", " ".join((
            _group("research", _fields([s("max_debate_rounds", "?")])),
            _group("risk", _fields([s("max_risk_discuss_rounds", "?")])),
        ))))
        vendors = {**(s("data_vendors") or {}), **(s("tool_vendors") or {})}
        if vendors:
            details.append(("Data vendors", " ".join(
                _group(_CATEGORY.get(k, k), _chain(v)) for k, v in vendors.items()
            )))
        details.append(("Version", escape(f"TradingAgents {s('version', '?')}")))
    if final_state.get("memory_note"):
        details.append(("Memory log", escape(final_state["memory_note"])))
    return details


def _market_snapshot(ticker: str, final_state: dict, settings: dict | None, cache_dir) -> str:
    """Build an offline price/SMA chart from the run's Yahoo cache, capped at its analysis date."""
    vendors = (settings or {}).get("data_vendors") or {}
    if "yfinance" not in str(vendors.get("core_stock_apis", "")).casefold():
        return ""
    trade_date = str(final_state.get("trade_date") or "")[:10]
    if not trade_date or not cache_dir:
        return ""
    try:
        safe_ticker = safe_ticker_component(ticker)
    except ValueError:
        return ""
    path = Path(cache_dir) / f"{safe_ticker}-YFin-data.csv"
    if not path.is_file():
        return ""

    rows = []
    try:
        with path.open(encoding="utf-8", newline="") as stream:
            for row in csv.DictReader(stream):
                bar_date = (row.get("Date") or row.get("Datetime") or "")[:10]
                try:
                    close = float(row["Close"])
                except (KeyError, TypeError, ValueError):
                    continue
                if bar_date and bar_date <= trade_date and close > 0:
                    rows.append((bar_date, close))
    except (OSError, UnicodeError):
        return ""
    if len(rows) < 20:
        return ""
    latest_date = rows[-1][0]
    try:
        lag = (datetime.fromisoformat(trade_date) - datetime.fromisoformat(latest_date)).days
    except ValueError:
        return ""
    if lag > 10:
        return ""

    rows.sort(key=lambda item: item[0])
    values = [close for _, close in rows]
    def rolling_mean(window):
        result = [None] * len(values)
        running = 0.0
        for idx, value in enumerate(values):
            running += value
            if idx >= window:
                running -= values[idx - window]
            if idx >= window - 1:
                result[idx] = running / window
        return result

    series = [("Close", values[-180:], "series-close")]
    sma50, sma200 = rolling_mean(50), rolling_mean(200)
    if any(value is not None for value in sma50[-180:]):
        series.append(("50-day SMA", sma50[-180:], "series-sma50"))
    if any(value is not None for value in sma200[-180:]):
        series.append(("200-day SMA", sma200[-180:], "series-sma200"))

    chart_start = max(0, len(values) - 180)
    visible_dates = [item[0] for item in rows[chart_start:]]
    visible_values = [v for _, seq, _ in series for v in seq if v is not None]
    low, high = min(visible_values), max(visible_values)
    padding = max((high - low) * 0.08, high * 0.002)
    low, high = low - padding, high + padding
    left, right, top, bottom = 76, 790, 24, 272
    width, height = right - left, bottom - top
    count = len(visible_dates)
    def x_at(index):
        return left + width * index / max(count - 1, 1)
    def y_at(value):
        return top + height * (high - value) / (high - low)

    grid = []
    for step in range(5):
        value = low + (high - low) * step / 4
        y = y_at(value)
        grid.append(
            f'<line class="gridline" x1="{left}" x2="{right}" y1="{y:.1f}" y2="{y:.1f}" />'
            f'<text class="axis-label" x="{left - 8}" y="{y + 4:.1f}" text-anchor="end">{value:,.0f}</text>'
        )
    plots = []
    legends = []
    for label, sequence, class_name in series:
        points = []
        for idx, value in enumerate(sequence):
            if value is not None:
                points.append(f"{x_at(idx):.1f},{y_at(value):.1f}")
        if len(points) > 1:
            plots.append(f'<polyline class="{class_name}" points="{" ".join(points)}" />')
        legends.append(f'<span><i class="legend-{class_name.removeprefix("series-")}"></i>{escape(label)}</span>')

    first_label = visible_dates[0][5:]
    last_label = visible_dates[-1][5:]
    close = values[-1]
    cards = [f'<div class="summary-card"><span>Latest cached close</span><strong>{close:,.2f}</strong><small>as of {escape(latest_date)}</small></div>']
    explanation = []
    for window, mean_series in ((50, sma50), (200, sma200)):
        average = mean_series[-1]
        if average is None:
            continue
        gap = (close / average - 1) * 100
        relation = "above" if gap >= 0 else "below"
        cards.append(f'<div class="summary-card"><span>{window}-day moving average</span><strong>{average:,.2f}</strong><small>close is {abs(gap):.1f}% {relation}</small></div>')
        explanation.append(f"The latest close is {abs(gap):.1f}% {relation} the {window}-day average.")
    if len(cards) == 1:
        cards.append('<div class="summary-card"><span>Long-term average</span><strong>Not available</strong><small>not enough cached history</small></div>')
    currency = "INR" if ticker.endswith((".NS", ".BO")) else "price units"
    chart = (
        '<section class="market-chart" aria-labelledby="price-history-title">'
        f'<h2 id="price-history-title">Price history and trend context</h2>'
        f'<p>Cached daily closes through {escape(latest_date)}; data after the analysis date is excluded. Values are in {currency}.</p>'
        f'<svg viewBox="0 0 820 310" role="img" aria-label="Daily closing price and available moving averages from {escape(first_label)} through {escape(last_label)}">'
        f'{"".join(grid)}<line class="gridline" x1="{left}" x2="{right}" y1="{bottom}" y2="{bottom}" />'
        f'{"".join(plots)}'
        f'<text class="axis-label" x="{left}" y="300">{escape(first_label)}</text>'
        f'<text class="axis-label" x="{right}" y="300" text-anchor="end">{escape(last_label)}</text></svg>'
        f'<div class="chart-legend">{"".join(legends)}</div>'
        f'<div class="reader-summary">{"".join(cards)}</div>'
        f'<p><strong>How to read it:</strong> {escape(" ".join(explanation))} Moving averages summarize historical prices; they are not forecasts. The chart is a cached data snapshot, not a live quote.</p>'
        '</section>'
    )
    return chart


def render_report(ticker: str, final_state: dict, settings: dict | None, parts, cache_dir=None) -> str:
    """The report page: title and rating, what produced the run, contents, sections."""
    md = _markdown()
    rating = run_rating(final_state) if final_state.get("final_trade_decision") else ""
    tone = _TONE.get(rating, "review")
    date = final_state.get("trade_date", "")

    title = f'<span class="ticker">{escape(ticker)}</span>'
    if rating:
        title += f' <span class="rating {tone}">{escape(rating)}</span>'
    details = "".join(
        f'<div class="{"note" if label == "Memory log" else "detail"}">'
        f"<dt>{escape(label)}</dt><dd>{value}</dd></div>"
        for label, value in _run_details(final_state, settings)
    )

    contents, body = [], []
    for n, (heading, _folder, written) in enumerate(parts, 1):
        agents = "".join(
            f'<li><a href="#s{n}-{m}"><span class="bar"></span> <span class="label">{escape(agent)}</span></a></li>'
            for m, (agent, _f, _t) in enumerate(written, 1)
        )
        numeral, _, name = heading.partition(". ")
        contents.append(f'<li><a href="#s{n}"><span class="num">{escape(numeral)}</span> '
                        f'<span class="label">{escape(name)}</span></a><ul>{agents}</ul></li>')
        body.append(f'<section id="s{n}"><h2>{escape(heading)}</h2>')
        for m, (agent, _filename, text) in enumerate(written, 1):
            body.append(f'<h3 id="s{n}-{m}">{escape(agent)}</h3>\n{_render_agent_text(md, text)}')
        body.append("</section>")

    page_title = " ".join(x for x in (ticker, date, rating) if x)
    analyst_count = len((settings or {}).get("analysts") or [])
    snapshot = _market_snapshot(ticker, final_state, settings, cache_dir)
    summary = (
        '<section class="reader-summary" aria-label="Run summary">'
        f'<div class="summary-card"><span>Final rating</span><strong>{escape(rating or "Not returned")}</strong><small>LLM-generated recommendation</small></div>'
        f'<div class="summary-card"><span>Analysis date</span><strong>{escape(date or "Not specified")}</strong><small>Historical cutoff for this run</small></div>'
        f'<div class="summary-card"><span>Selected analysts</span><strong>{analyst_count}</strong><small>Specialist roles configured</small></div>'
        '</section>'
    )
    workflow = (
        '<aside class="report-guide"><h2>How this report is organized</h2>'
        '<p><strong>Analysts</strong> gather price, news, sentiment, and company evidence. '
        '<strong>Research</strong> compares bullish and bearish cases. <strong>Trading</strong> proposes a plan. '
        '<strong>Risk</strong> reviews the plan, and the <strong>Portfolio Manager</strong> produces the final rating.</p>'
        '<p>These are model-generated judgments. Check the data-availability section before relying on a claim; an unavailable feed is not proof that no event occurred.</p></aside>'
    )
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'">
<title>{escape(page_title)}: TradingAgents report</title>
<style>{_CSS}</style>
</head>
<body>
<div class="page" id="top">
<header class="masthead">
<a class="logo" href="{_COMPANY}" rel="noopener" aria-label="Tauric Research">{_LOGO}</a>
<h1>{title}</h1>
<p class="date">{escape(f"Analysis of {date}" if date else "Analysis")}</p>
<dl class="run">{details}</dl>
{_rating_visual(rating)}
</header>
<nav class="contents" aria-label="Sections"><ul>{"".join(contents)}</ul></nav>
<main>
{summary}
{workflow}
{snapshot}
{"".join(body)}
</main>
<footer class="credit"><a href="{_PROJECT}" rel="noopener">TradingAgents</a> powered by <a class="brand" href="{_ORG}" rel="noopener">Tauric Research</a></footer>
</div>
<a class="to-top" href="#top">Top</a>
</body>
</html>
"""


def _rating_visual(rating: str) -> str:
    """Render the agent's categorical rating on an ordinal scale, not as a forecast."""
    if not rating:
        return ""
    steps = ("Sell", "Underweight", "Hold", "Overweight", "Buy")
    rendered_steps = []
    for step in steps:
        active = step == rating
        current = ' aria-current="true"' if active else ""
        rendered_steps.append(
            f'<div class="rating-step {_TONE.get(step, "level")}{" active" if active else ""}"'
            f'{current}>{escape(step)}</div>'
        )
    rendered = "".join(rendered_steps)
    return (
        f'<div class="decision-visual" role="img" aria-label="Agent rating: {escape(rating)} on a five-level scale">'
        f'<p class="decision-visual-title">Agent rating · categorical output</p>'
        f'<div class="rating-spectrum">{rendered}</div></div>'
    )
