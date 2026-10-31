"""Reusable report-tree writer shared by the CLI and the programmatic API.

Writes a run's per-section markdown (analysts, research, trading, risk,
portfolio) plus a consolidated ``complete_report.md`` under ``save_path``. The
CLI and ``TradingAgentsGraph.save_reports`` both call this, so a headless / API
run produces the same on-disk report tree a CLI run does.
"""

from datetime import datetime
from pathlib import Path

from tradingagents.agents.rating import run_rating


def analyst_names(keys) -> list[str]:
    """The analysts as users select them: the sentiment analyst's key is "social"."""
    return ["sentiment" if key == "social" else key for key in keys or []]


def _header(ticker: str, final_state: dict, settings: dict | None) -> str:
    """The report's title and what produced it: analysis date, version, models, analysts, vendors."""
    lines = [f"# Trading Analysis Report: {ticker}", ""]
    if final_state.get("trade_date"):
        lines.append(f"- Analysis date: {final_state['trade_date']}")
    if final_state.get("final_trade_decision"):
        lines.append(f"- Rating: {run_rating(final_state)}")
    lines.append(f"- Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    if settings:
        s = settings.get
        deep_provider = s("deep_think_provider") or s("llm_provider", "?")
        quick_provider = s("quick_think_provider") or s("llm_provider", "?")
        if deep_provider == quick_provider:
            models = f"{deep_provider}, deep {s('deep_think_llm', '?')}, quick {s('quick_think_llm', '?')}"
        else:   # each tier on its own provider (#1440)
            models = (f"deep {deep_provider} {s('deep_think_llm', '?')}, "
                      f"quick {quick_provider} {s('quick_think_llm', '?')}")
        lines.append(f"- TradingAgents {s('version', '?')}: {models}")
        lines.append(f"- Analysts: {', '.join(analyst_names(s('analysts')))}; "
                     f"research debate rounds {s('max_debate_rounds', '?')}, "
                     f"risk debate rounds {s('max_risk_discuss_rounds', '?')}")
        vendors = {**(s("data_vendors") or {}), **(s("tool_vendors") or {})}
        if vendors:
            lines.append("- Data vendors: " + ", ".join(f"{k} {v}" for k, v in vendors.items()))
    if final_state.get("memory_note"):
        lines.append(f"- Memory log: {final_state['memory_note']}")
    return "\n".join(lines) + "\n\n"


# The report's sections in order: (heading, folder, [(agent, file, state path)]).
_SECTIONS = (
    ("I. Analyst Team Reports", "1_analysts", (
        ("Market Analyst", "market.md", ("market_report",)),
        ("Sentiment Analyst", "sentiment.md", ("sentiment_report",)),
        ("News Analyst", "news.md", ("news_report",)),
        ("Fundamentals Analyst", "fundamentals.md", ("fundamentals_report",)),
    )),
    ("II. Research Team Decision", "2_research", (
        ("Bull Researcher", "bull.md", ("investment_debate_state", "bull_history")),
        ("Bear Researcher", "bear.md", ("investment_debate_state", "bear_history")),
        ("Research Manager", "manager.md", ("investment_plan",)),
    )),
    ("III. Trading Team Plan", "3_trading", (
        ("Trader", "trader.md", ("trader_investment_plan",)),
    )),
    ("IV. Risk Management Team Decision", "4_risk", (
        ("Aggressive Analyst", "aggressive.md", ("risk_debate_state", "aggressive_history")),
        ("Conservative Analyst", "conservative.md", ("risk_debate_state", "conservative_history")),
        ("Neutral Analyst", "neutral.md", ("risk_debate_state", "neutral_history")),
    )),
    ("V. Portfolio Manager Decision", "5_portfolio", (
        ("Portfolio Manager", "decision.md", ("final_trade_decision",)),
    )),
)

_AVAILABILITY_SECTION = ("0. Data Availability and Evidence", "0_data_availability", (
    ("How to read source coverage", "availability.md", ("data_availability_note",)),
))

_UNAVAILABLE_MARKERS = (
    "data_unavailable", "no_data_available", "unavailable", "not configured",
    "missing api key", "api key missing", "network error", "connection reset",
    "failed to fetch", "could not retrieve", "could not be retrieved",
)


def _data_availability_note(final_state: dict) -> str:
    """Add a reader-facing guard between missing feeds and LLM conclusions.

    Vendor response metadata is not preserved in every graph state, so this
    summary is explicitly attributed to what the agent reports. It never claims
    an independent audit of the provider response.
    """
    source_reports = {
        "news_report": str(final_state.get("news_report") or ""),
        "market_report": str(final_state.get("market_report") or ""),
        "fundamentals_report": str(final_state.get("fundamentals_report") or ""),
        "sentiment_report": str(final_state.get("sentiment_report") or ""),
    }

    def unavailable(text: str) -> bool:
        lowered = text.casefold()
        return any(marker in lowered for marker in _UNAVAILABLE_MARKERS)

    findings = []
    news = source_reports["news_report"]
    if unavailable(news) and any(term in news.casefold() for term in ("company news", "specific news", "news feed", "news articles")):
        findings.append(
            "- **Company news:** The News Analyst report says the news input was unavailable. "
            "This run cannot verify whether company headlines existed; do not interpret the missing feed as no news."
        )
    if unavailable(news) and any(term in news.casefold() for term in ("macro", "fred", "treasury", "fed rates")):
        findings.append(
            "- **Macro indicators:** The News Analyst report says one or more macro inputs were unavailable. "
            "Any general macro discussion is context or model inference, not a measured value from those feeds."
        )
    if unavailable(news) and any(term in news.casefold() for term in ("prediction market", "polymarket", "market-implied probabilities")):
        findings.append(
            "- **Prediction markets:** The News Analyst report says this input was unavailable. "
            "No probability estimate was measured, and this does not mean no relevant event risk exists."
        )
    if unavailable(source_reports["market_report"]):
        findings.append("- **Prices or indicators:** The Market Analyst report says one or more market inputs were unavailable; verify affected values before citing them.")
    if unavailable(source_reports["fundamentals_report"]):
        findings.append("- **Fundamentals:** The Fundamentals Analyst report says one or more inputs were unavailable; do not treat missing fields as zero or as evidence of absence.")
    if unavailable(source_reports["sentiment_report"]):
        findings.append("- **Social sentiment:** The Sentiment Analyst report says one or more sources were unavailable; its coverage and confidence may be limited.")

    if not findings:
        findings.append(
            "- Agent reports did not explicitly flag a monitored source as unavailable. "
            "This is not an independent completeness check of provider responses."
        )

    return "\n".join([
        "**Coverage status below is taken from the analyst reports, not independent API telemetry.** "
        "An unavailable input means the run received no usable evidence from that source; it does not establish that no event, headline, or risk existed.",
        "",
        *findings,
        "",
        "**Evidence boundary:** Analyst narratives and summary tables are LLM-generated. Verify factual or numeric claims against retrieved source material before citing them; general commentary must not be presented as a measurement from an unavailable feed.",
    ])


def _report_parts(final_state: dict) -> list[tuple[str, str, list[tuple[str, str, str]]]]:
    """The sections with something to say: (heading, folder, [(agent, file, text)])."""
    parts = [(
        _AVAILABILITY_SECTION[0], _AVAILABILITY_SECTION[1],
        [("Coverage status and interpretation limits", "availability.md", _data_availability_note(final_state))],
    )]
    for heading, folder, agents in _SECTIONS:
        written = []
        for agent, filename, path in agents:
            value = final_state
            for key in path:
                value = (value or {}).get(key)
            if value:
                written.append((agent, filename, value))
        if written:
            parts.append((heading, folder, written))
    return parts


def write_report_tree(final_state: dict, ticker: str, save_path, settings: dict | None = None,
                      html: bool = True, cache_dir=None) -> Path:
    """Save a completed run's reports to ``save_path``; return the complete-report path.

    ``settings`` (``TradingAgentsGraph.run_settings()``) adds what produced the run
    to the report's header. ``html`` also writes ``complete_report.html``, one
    self-contained page of the same report (#1419).
    Reusing a directory replaces the generated report files, removing sections
    absent from this run and disabled HTML. Other files and directories are kept.
    """
    save_path = Path(save_path)
    save_path.mkdir(parents=True, exist_ok=True)
    parts = _report_parts(final_state)
    sections = []
    for heading, folder, written in parts:
        (save_path / folder).mkdir(exist_ok=True)
        for _agent, filename, text in written:
            (save_path / folder / filename).write_text(text, encoding="utf-8")
        content = "\n\n".join(f"### {agent}\n{text}" for agent, _filename, text in written)
        sections.append(f"## {heading}\n\n{content}")

    (save_path / "complete_report.md").write_text(
        _header(ticker, final_state, settings) + "\n\n".join(sections), encoding="utf-8"
    )
    if html:
        from tradingagents.report_html import render_report

        (save_path / "complete_report.html").write_text(
            render_report(ticker, final_state, settings, parts, cache_dir=cache_dir), encoding="utf-8"
        )
    else:
        (save_path / "complete_report.html").unlink(missing_ok=True)

    # Reconcile only the filenames owned by this writer; never clear the tree,
    # since callers may keep notes or other artifacts alongside the reports.
    current_files = {
        (folder, filename)
        for _heading, folder, written in parts
        for _agent, filename, _text in written
    }
    for _heading, folder, agents in (_AVAILABILITY_SECTION, *_SECTIONS):
        for _agent, filename, _path in agents:
            if (folder, filename) not in current_files:
                (save_path / folder / filename).unlink(missing_ok=True)
    return save_path / "complete_report.md"
