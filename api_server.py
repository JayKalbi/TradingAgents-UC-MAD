"""Local HTTP API for the React TradingAgents dashboard."""

from __future__ import annotations

import json
import math
import os
import shutil
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from dataclasses import asdict
from datetime import date
from pathlib import Path
from typing import Literal

import yfinance as yf
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from tradingagents.agents.rating import run_rating
from tradingagents.backtest import run_backtest
from tradingagents.compare import compare_backtests, write_comparison
from tradingagents.dataflows.config import run_config
from tradingagents.dataflows.symbols import crypto_base, normalize_symbol, safe_ticker_component
from tradingagents.default_config import DEFAULT_CONFIG

# Importing TradingAgents loads the repository's .env file.
from tradingagents.graph.trading_graph import TradingAgentsGraph
from tradingagents.memory import TradingMemoryLog
from tradingagents.memory.settlement import fetch_returns, resolve_benchmark

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / ".tradingagents-data"
RESULTS_DIR = DATA_DIR / "results"
REPORTS_DIR = RESULTS_DIR / "reports"
EXPERIMENTS_DIR = RESULTS_DIR / "experiments"
YFINANCE_CACHE_DIR = DATA_DIR / "yfinance-cache"
DATA_DIR.mkdir(parents=True, exist_ok=True)
YFINANCE_CACHE_DIR.mkdir(parents=True, exist_ok=True)
# yfinance's default SQLite cache may land in a protected Windows profile or
# service account directory. Keep its cookie/timezone DB inside this project.
yf.set_tz_cache_location(str(YFINANCE_CACHE_DIR))
ALLOWED_ANALYSTS = {"market", "social", "news", "fundamentals"}
ALLOWED_MODELS = {"gemini-3.5-flash-lite", "gemini-3.1-flash-lite"}

app = FastAPI(title="TradingAgents Local API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)

# TradingAgents has process-level data-vendor configuration; serialize LLM jobs
# so concurrent runs cannot overwrite each other's active settings.
_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="tradingagents-job")
_jobs: dict[str, dict] = {}
_jobs_lock = threading.Lock()
_market_cache: dict[tuple[str, str], tuple[float, dict]] = {}
_market_lock = threading.Lock()
_company_search_cache: dict[str, tuple[float, list[dict]]] = {}
_MARKET_CACHE_SECONDS = 60


class AnalysisRequest(BaseModel):
    ticker: str = Field(min_length=1, max_length=32)
    analysis_date: date | None = None
    analysts: list[str] = Field(default_factory=lambda: ["market"])
    model: str = "gemini-3.5-flash-lite"
    max_tool_rounds: int = Field(default=3, ge=2, le=6)


class ExperimentRequest(BaseModel):
    tickers: list[str] = Field(min_length=1, max_length=4)
    dates: list[date] = Field(min_length=1, max_length=6)
    model: str = "gemini-3.5-flash-lite"
    max_tool_rounds: int = Field(default=3, ge=2, le=6)


def _config(model: str, max_tool_rounds: int) -> dict:
    if model not in ALLOWED_MODELS:
        raise ValueError(f"Unsupported model: {model}")
    cfg = deepcopy(DEFAULT_CONFIG)
    cfg.update({
        "results_dir": str(RESULTS_DIR),
        "data_cache_dir": str(DATA_DIR / "cache"),
        "memory_log_path": str(DATA_DIR / "memory" / "trading_memory.md"),
        "llm_provider": "google",
        "quick_think_provider": None,
        "deep_think_provider": None,
        "quick_think_llm": model,
        "deep_think_llm": model,
        "google_thinking_level": "minimal",
        "output_language": "English",
        "max_debate_rounds": 1,
        "max_risk_discuss_rounds": 1,
        "max_tool_rounds": max_tool_rounds,
        "max_tokens": 1024,
        "llm_max_retries": 2,
    })
    return cfg


def _settle_research_outcomes(run_id: str, config: dict) -> tuple[int, list[str]]:
    """Settle research outcomes from prices without requiring an LLM reflection.

    The experiment measures realized alpha. A reflective paragraph is not part
    of that metric, so quota/network failure in the optional reflection step
    must not leave otherwise measurable cells unscored.
    """
    log_path = RESULTS_DIR / "backtest" / run_id / "trading_memory.md"
    log = TradingMemoryLog({"memory_log_path": str(log_path)})
    settled = 0
    unresolved: list[str] = []
    for entry in log.get_pending_entries():
        ticker, trade_date = entry["ticker"], entry["date"]
        try:
            with run_config(config):
                raw, alpha, days, resolution_date = fetch_returns(
                    ticker,
                    trade_date,
                    config.get("holding_period_days", 5),
                    benchmark=resolve_benchmark(ticker, config),
                )
            if raw is None or alpha is None or days is None:
                unresolved.append(f"{ticker} {trade_date}: holding window is not settled yet")
                continue
            reflection = (
                "Research experiment outcome: realized return and benchmark-relative alpha "
                "were calculated from historical market closes; no LLM reflection was used."
            )
            if log.update_with_outcome(
                ticker, trade_date, raw, alpha, days, reflection,
                resolution_date=resolution_date,
            ):
                settled += 1
        except Exception as exc:
            message = str(exc)
            secret = os.environ.get("GOOGLE_API_KEY")
            if secret:
                message = message.replace(secret, "[API key hidden]")
            unresolved.append(f"{ticker} {trade_date}: {type(exc).__name__}: {message[:180]}")
    return settled, unresolved


def _experiment_result_payload(comparison, experiment_id: str, metadata: dict) -> dict:
    return {
        "question": "How does analyst-team composition affect rating-weighted benchmark-relative outcomes?",
        "tickers": metadata.get("tickers", []),
        "dates": metadata.get("dates", []),
        "model": metadata.get("model", "saved run configuration"),
        "experiment_id": experiment_id,
        "runs": metadata.get("conditions", []),
        "matched_cases": len(comparison.cells),
        "mean_alpha_baseline": comparison.mean_alpha_a,
        "mean_alpha_expanded": comparison.mean_alpha_b,
        "mean_rating_alpha_baseline": comparison.mean_rating_alpha_a,
        "mean_rating_alpha_expanded": comparison.mean_rating_alpha_b,
        "mean_delta": comparison.mean_rating_delta,
        "ci_low": comparison.rating_ci_low,
        "ci_high": comparison.rating_ci_high,
        "p_value": comparison.rating_p_value,
        "test_method": comparison.rating_test_method,
        "directional_accuracy_baseline": comparison.directional_accuracy_a,
        "directional_accuracy_expanded": comparison.directional_accuracy_b,
        "directional_cases_baseline": comparison.directional_cases_a,
        "directional_cases_expanded": comparison.directional_cases_b,
        "directional_coverage_baseline": comparison.directional_coverage_a,
        "directional_coverage_expanded": comparison.directional_coverage_b,
        "paired_directional_cases": comparison.paired_directional_cases,
        "paired_accuracy_delta": comparison.paired_accuracy_delta,
        "accuracy_ci_low": comparison.accuracy_ci_low,
        "accuracy_ci_high": comparison.accuracy_ci_high,
        "accuracy_p_value": comparison.accuracy_p_value,
        "coverage_delta": comparison.coverage_delta,
        "coverage_ci_low": comparison.coverage_ci_low,
        "coverage_ci_high": comparison.coverage_ci_high,
        "coverage_p_value": comparison.coverage_p_value,
        "cells": [
            {
                "ticker": cell.ticker,
                "date": cell.date,
                "baseline_rating": cell.rating_a,
                "baseline_alpha": cell.alpha_a,
                "baseline_rating_alpha": cell.rating_alpha_a,
                "baseline_direction_correct": cell.directional_correct_a,
                "expanded_rating": cell.rating_b,
                "expanded_alpha": cell.alpha_b,
                "expanded_rating_alpha": cell.rating_alpha_b,
                "expanded_direction_correct": cell.directional_correct_b,
                "delta": cell.delta,
                "rating_alpha_delta": cell.rating_delta,
            }
            for cell in comparison.cells
        ],
        "warnings": [
            "Directional accuracy excludes neutral calls and zero rounded alpha; coverage is reported separately.",
            "The rating-weighted alpha is a normalized signal proxy, not an execution backtest.",
            "Small samples are exploratory; alpha is rounded and text feeds are not archived.",
        ],
    }


def _save_recalculated_experiment(experiment_dir: Path, metadata: dict, comparison) -> dict:
    experiment_id = experiment_dir.name
    html_path, csv_path = write_comparison(comparison, experiment_dir)
    shutil.copyfile(html_path, experiment_dir / "comparison.html")
    shutil.copyfile(csv_path, experiment_dir / "paired_cells.csv")
    metadata["question"] = "How does analyst-team composition affect rating-weighted benchmark-relative outcomes?"
    metadata["metric_version"] = "rating-weighted-alpha-directional-v1"
    metadata["comparison"] = asdict(comparison)
    metadata["comparison_html"] = "comparison.html"
    metadata["paired_csv"] = "paired_cells.csv"
    metadata["comparison_method"] = "Recalculated from saved backtest logs; no LLM calls"
    (experiment_dir / "experiment.json").write_text(
        json.dumps(metadata, indent=2, default=str), encoding="utf-8"
    )
    return _experiment_result_payload(comparison, experiment_id, metadata)


def _validate_ticker(value: str) -> str:
    try:
        normalized = normalize_symbol(value.strip())
        safe_ticker_component(normalized)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None
    return normalized


def _check_llm(model: str) -> None:
    if not os.environ.get("GOOGLE_API_KEY"):
        raise HTTPException(
            status_code=503,
            detail="GOOGLE_API_KEY is not set. Add it to the repository .env file and restart the API.",
        )
    if model not in ALLOWED_MODELS:
        raise HTTPException(status_code=422, detail="Choose a supported Gemini Flash-Lite model.")


def _new_job(kind: str, worker) -> str:
    job_id = uuid.uuid4().hex[:12]
    with _jobs_lock:
        _jobs[job_id] = {
            "id": job_id,
            "kind": kind,
            "status": "queued",
            "progress": 0,
            "message": "Waiting to start",
            "result": None,
            "error": None,
            "created_at": time.time(),
        }

    def update(**changes):
        with _jobs_lock:
            if job_id in _jobs:
                _jobs[job_id].update(changes)

    def execute():
        update(status="running", message="Starting the agent workflow")
        try:
            result = worker(update)
            update(status="completed", progress=100, message="Complete", result=result)
        except Exception as exc:  # show a concise error without ever exposing a key
            message = str(exc)
            if "WinError 10013" in message or "10013" in message and "socket" in message.lower():
                message = (
                    "Windows denied the outbound network connection. Start this API from a normal "
                    "PowerShell window (not a restricted Codex terminal), or allow this Python "
                    "environment through Windows Firewall, then restart the API."
                )
            key = os.environ.get("GOOGLE_API_KEY")
            if key:
                message = message.replace(key, "[API key hidden]")
            update(status="failed", message="Run failed", error=message[:900])

    _executor.submit(execute)
    return job_id


def _market_data(ticker: str, period: str) -> dict:
    symbol = _validate_ticker(ticker)
    key = (symbol, period)
    now = time.monotonic()
    with _market_lock:
        cached = _market_cache.get(key)
        if cached and now - cached[0] < _MARKET_CACHE_SECONDS:
            return cached[1]

    history = yf.Ticker(symbol).history(period=period, interval="1d", auto_adjust=False)
    if history is None or history.empty or "Close" not in history:
        raise HTTPException(status_code=404, detail=f"No Yahoo Finance price history found for {symbol}.")
    history = history.dropna(subset=["Close"])
    close = history["Close"].astype(float)
    delta = close.diff()
    average_gain = delta.clip(lower=0).rolling(14).mean()
    average_loss = -delta.clip(upper=0).rolling(14).mean()
    relative_strength = average_gain / average_loss.replace(0, float("nan"))
    rsi_series = 100 - (100 / (1 + relative_strength))
    rsi = float(rsi_series.iloc[-1]) if not rsi_series.empty else float("nan")
    last_close = float(close.iloc[-1])
    previous_close = float(close.iloc[-2]) if len(close) > 1 else last_close
    quote_price = last_close
    quote_as_of = history.index[-1].isoformat()
    source = "Yahoo Finance daily close"

    # Intraday bars are best-effort; the daily close remains the reliable fallback.
    try:
        intraday = yf.Ticker(symbol).history(period="1d", interval="15m", auto_adjust=False)
        if intraday is not None and not intraday.empty and intraday["Close"].dropna().size:
            quote_price = float(intraday["Close"].dropna().iloc[-1])
            quote_as_of = intraday["Close"].dropna().index[-1].isoformat()
            source = "Yahoo Finance latest intraday bar"
    except Exception:
        pass

    bars = []
    for timestamp, row in history.tail(260).iterrows():
        volume = row.get("Volume")
        bars.append({
            "date": timestamp.strftime("%Y-%m-%d"),
            "close": round(float(row["Close"]), 4),
            "volume": int(volume) if volume is not None and math.isfinite(float(volume)) else 0,
        })

    result = {
        "ticker": ticker.strip().upper(),
        "symbol": symbol,
        "currency": "points" if symbol.startswith("^") else "local currency",
        "price": round(quote_price, 4),
        "previous_close": round(previous_close, 4),
        "change_pct": round((quote_price / previous_close - 1) * 100, 3) if previous_close else 0,
        "rsi_14": round(rsi, 2) if math.isfinite(rsi) else None,
        "as_of": quote_as_of,
        "source": source,
        "bars": bars,
        "settled_dates": [bar["date"] for bar in bars[:-6][-30:]],
        "disclaimer": "Yahoo Finance data may be delayed, incomplete, or unavailable for some exchanges.",
    }
    with _market_lock:
        _market_cache[key] = (now, result)
    return result


@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "llm_provider": "google",
        "api_key_configured": bool(os.environ.get("GOOGLE_API_KEY")),
        "default_model": "gemini-3.5-flash-lite",
        "market_data": "Yahoo Finance via yfinance",
    }


@app.get("/api/companies/search")
def search_indian_companies(q: str = Query(min_length=2, max_length=80)):
    """Search Yahoo Finance listings and return Indian NSE/BSE equities only."""
    query = q.strip()
    if len(query) < 2:
        raise HTTPException(status_code=422, detail="Enter at least two characters to search.")
    cache_key = query.casefold()
    now = time.monotonic()
    cached = _company_search_cache.get(cache_key)
    if cached and now - cached[0] < _MARKET_CACHE_SECONDS:
        return {"query": query, "results": cached[1], "source": "Yahoo Finance search"}
    try:
        search = yf.Search(query, max_results=20, news_count=0, lists_count=0)
        results = []
        seen = set()
        for quote in search.quotes:
            symbol = str(quote.get("symbol", "")).upper()
            if not symbol.endswith((".NS", ".BO")) or symbol in seen:
                continue
            if quote.get("quoteType") not in (None, "EQUITY"):
                continue
            seen.add(symbol)
            results.append({
                "symbol": symbol,
                "name": quote.get("longname") or quote.get("shortname") or symbol,
                "exchange": quote.get("exchDisp") or quote.get("exchange") or ("NSE" if symbol.endswith(".NS") else "BSE"),
                "quote_type": quote.get("quoteType") or "EQUITY",
            })
        _company_search_cache[cache_key] = (now, results)
        return {"query": query, "results": results, "source": "Yahoo Finance search"}
    except Exception as exc:
        message = str(exc)
        if "WinError 10013" in message or "10013" in message and "socket" in message.lower():
            message = "Windows denied outbound access to Yahoo Finance. Run the API from a normal PowerShell window."
        raise HTTPException(status_code=502, detail=f"Company search failed: {message[:220]}") from None


@app.get("/api/market")
def market(ticker: str = Query(min_length=1, max_length=32), period: Literal["1mo", "3mo", "6mo", "1y"] = "3mo"):
    try:
        return _market_data(ticker, period)
    except HTTPException:
        raise
    except Exception as exc:
        message = str(exc)
        if "unable to open database file" in message.lower():
            message = (
                "Yahoo Finance cache could not be opened. Restart the API after the project-local "
                "cache directory is created, and make sure the project folder is writable."
            )
        elif "WinError 10013" in message or "10013" in message and "socket" in message.lower():
            message = "Windows denied outbound network access to Yahoo Finance. Run the API from a normal PowerShell window."
        raise HTTPException(status_code=502, detail=f"Market data request failed: {message[:240]}") from None


@app.post("/api/analyze")
def start_analysis(request: AnalysisRequest):
    _check_llm(request.model)
    if not request.analysts or any(item not in ALLOWED_ANALYSTS for item in request.analysts):
        raise HTTPException(status_code=422, detail="Select one or more supported analyst roles.")
    ticker = _validate_ticker(request.ticker)
    analysis_date = request.analysis_date or date.today()
    if analysis_date > date.today():
        raise HTTPException(status_code=422, detail="Analysis date cannot be in the future.")
    asset_type = "crypto" if crypto_base(ticker) else "stock"

    def worker(update):
        cfg = _config(request.model, request.max_tool_rounds)
        graph = TradingAgentsGraph(request.analysts, config=cfg)
        update(message=f"Running {len(request.analysts)} analyst role(s) and the decision workflow")
        state, signal = graph.propagate(ticker, analysis_date.isoformat(), asset_type=asset_type)
        report_md = graph.save_reports(state, ticker, html=True)
        report_id = report_md.parent.name
        return {
            "ticker": ticker,
            "asset_type": asset_type,
            "analysis_date": analysis_date.isoformat(),
            "rating": run_rating(state),
            "signal": str(signal),
            "report_id": report_id,
            "model": request.model,
            "analysts": request.analysts,
        }

    return {"job_id": _new_job("analysis", worker)}


@app.post("/api/experiment")
def start_experiment(request: ExperimentRequest):
    _check_llm(request.model)
    tickers = [_validate_ticker(ticker) for ticker in request.tickers]
    if any(crypto_base(ticker) for ticker in tickers):
        raise HTTPException(status_code=422, detail="The India equity experiment accepts stock tickers, not crypto.")
    if any(not ticker.endswith((".NS", ".BO")) for ticker in tickers):
        raise HTTPException(status_code=422, detail="Search for an Indian NSE (.NS) or BSE (.BO) listing for this India-market experiment.")
    dates = [item.isoformat() for item in request.dates]
    if any(item >= date.today() for item in request.dates):
        raise HTTPException(status_code=422, detail="Choose historical dates so the five-trading-day outcome can settle.")
    if len(set(dates)) != len(dates):
        raise HTTPException(status_code=422, detail="Duplicate dates are not allowed.")

    def worker(update):
        cfg = _config(request.model, request.max_tool_rounds)
        runs = []
        conditions = [
            ("Market-only baseline", ["market"]),
            ("Expanded analyst team", ["market", "news", "fundamentals"]),
        ]
        for condition_index, (label, analysts) in enumerate(conditions):
            update(
                progress=int(condition_index * 50),
                message=f"Condition {condition_index + 1}/2: {label}",
            )

            def make_progress(idx=condition_index, tag=label):
                def progress(done, cells, current_ticker, current_date):
                    percentage = int(((idx + (done / max(cells, 1))) / 2) * 100)
                    update(
                        progress=percentage,
                        message=f"{tag}: {current_ticker} on {current_date} ({done}/{cells})",
                    )
                return progress

            result = run_backtest(
                tickers,
                dates,
                cfg,
                asset_type="stock",
                selected_analysts=analysts,
                progress=make_progress(),
            )
            runs.append({"label": label, "id": result.run_id, "analysts": analysts,
                         "failures": len(result.failures),
                         "settlement_failures": len(result.settlement_failures),
                         "cells_run": result.cells_run})

        update(progress=86, message="Settling price outcomes for the matched comparison")
        settlement_diagnostics = {}
        for run in runs:
            count, unresolved = _settle_research_outcomes(run["id"], cfg)
            run["deterministically_settled"] = count
            run["unresolved_outcomes"] = unresolved[:3]
            run["unresolved_count"] = len(unresolved)
            settlement_diagnostics[run["label"]] = {"settled": count, "unresolved": unresolved}

        update(progress=92, message="Pairing settled outcomes and calculating uncertainty")
        try:
            comparison = compare_backtests(runs[0]["id"], runs[1]["id"], RESULTS_DIR)
        except ValueError as exc:
            details = "; ".join(
                f"{run['label']} run {run['id']}: {run['cells_run']} cells ran, "
                f"{run['failures']} execution failures, "
                f"{run['unresolved_count']} outcomes unresolved"
                for run in runs
            )
            pending_reasons = "; ".join(
                f"{label}: {', '.join(info['unresolved'][:2])}"
                for label, info in settlement_diagnostics.items() if info["unresolved"]
            )
            raise RuntimeError(
                f"No paired settled outcomes were available. {details}. "
                f"{pending_reasons or str(exc)}"
            ) from exc
        experiment_id = uuid.uuid4().hex[:12]
        output_dir = EXPERIMENTS_DIR / experiment_id
        output_dir.mkdir(parents=True, exist_ok=True)
        return _save_recalculated_experiment(output_dir, {
            "question": "How does analyst-team composition affect rating-weighted benchmark-relative outcomes?",
            "tickers": tickers,
            "dates": dates,
            "model": request.model,
            "conditions": runs,
            "outcome_settlement": "deterministic historical prices; no LLM reflection required",
        }, comparison)

    return {"job_id": _new_job("experiment", worker)}


@app.get("/api/jobs/{job_id}")
def get_job(job_id: str):
    with _jobs_lock:
        job = _jobs.get(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found or server restarted.")
        return {key: value for key, value in job.items() if key != "created_at"}


@app.get("/api/reports")
def list_reports():
    reports = []
    if REPORTS_DIR.exists():
        for markdown_path in REPORTS_DIR.glob("*/complete_report.md"):
            text = markdown_path.read_text(encoding="utf-8")
            lines = text.splitlines()
            reports.append({
                "id": markdown_path.parent.name,
                "title": lines[0].lstrip("# ") if lines else markdown_path.parent.name,
                "metadata": [line[2:] for line in lines[1:8] if line.startswith("- ")],
                "has_html": (markdown_path.parent / "complete_report.html").is_file(),
                "modified": markdown_path.stat().st_mtime,
            })
    return sorted(reports, key=lambda row: row["modified"], reverse=True)


@app.get("/api/reports/{report_id}")
def get_report(report_id: str):
    safe_ticker_component(report_id, max_len=80)
    report_root = REPORTS_DIR.resolve()
    path = (REPORTS_DIR / report_id / "complete_report.md").resolve()
    if not path.is_relative_to(report_root) or not path.is_file():
        raise HTTPException(status_code=404, detail="Report not found.")
    return {"id": report_id, "markdown": path.read_text(encoding="utf-8")}


@app.get("/api/reports/{report_id}/html")
def download_report_html(report_id: str):
    safe_ticker_component(report_id, max_len=80)
    report_root = REPORTS_DIR.resolve()
    path = (REPORTS_DIR / report_id / "complete_report.html").resolve()
    if not path.is_relative_to(report_root) or not path.is_file():
        raise HTTPException(status_code=404, detail="HTML report not found.")
    return FileResponse(path, media_type="text/html", filename=path.name)


@app.get("/api/experiments")
def list_experiments():
    saved = []
    if not EXPERIMENTS_DIR.exists():
        return saved
    for metadata_path in EXPERIMENTS_DIR.glob("*/experiment.json"):
        try:
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            conditions = metadata.get("conditions", [])
            saved.append({
                "id": metadata_path.parent.name,
                "question": metadata.get("question", "Saved paired experiment"),
                "tickers": metadata.get("tickers", []),
                "dates": metadata.get("dates", []),
                "model": metadata.get("model", "unknown"),
                "run_a": conditions[0].get("id") if len(conditions) > 0 else None,
                "run_b": conditions[1].get("id") if len(conditions) > 1 else None,
                "modified": metadata_path.stat().st_mtime,
            })
        except (OSError, ValueError, TypeError):
            continue
    return sorted(saved, key=lambda item: item["modified"], reverse=True)


@app.post("/api/experiments/{experiment_id}/recalculate")
def recalculate_saved_experiment(experiment_id: str):
    """Re-score a saved comparison from local backtest logs, without LLM calls."""
    try:
        safe_id = safe_ticker_component(experiment_id, max_len=80)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None
    experiment_dir = (EXPERIMENTS_DIR / safe_id).resolve()
    if not experiment_dir.is_relative_to(EXPERIMENTS_DIR.resolve()):
        raise HTTPException(status_code=422, detail="Invalid experiment id.")
    metadata_path = experiment_dir / "experiment.json"
    if not metadata_path.is_file():
        raise HTTPException(status_code=404, detail="Saved experiment metadata was not found.")
    try:
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        conditions = metadata.get("conditions", [])
        if len(conditions) < 2 or not conditions[0].get("id") or not conditions[1].get("id"):
            raise ValueError("This saved experiment does not contain two backtest run ids.")
        run_a = safe_ticker_component(conditions[0]["id"], max_len=80)
        run_b = safe_ticker_component(conditions[1]["id"], max_len=80)
        model = metadata.get("model")
        cfg = _config(model if model in ALLOWED_MODELS else "gemini-3.5-flash-lite", 3)
        # Pending outcomes may be completed from Yahoo prices. This path never
        # constructs an LLM client or makes Gemini requests.
        unresolved = []
        for run_id in (run_a, run_b):
            _, pending = _settle_research_outcomes(run_id, cfg)
            unresolved.extend(pending)
        if unresolved:
            raise ValueError("Some saved outcomes are still unavailable: " + "; ".join(unresolved[:4]))
        comparison = compare_backtests(run_a, run_b, RESULTS_DIR)
        return _save_recalculated_experiment(experiment_dir, metadata, comparison)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from None
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Could not recalculate saved experiment: {str(exc)[:300]}") from None


@app.get("/api/experiments/{experiment_id}/{file_name}")
def download_experiment_file(experiment_id: str, file_name: Literal["comparison.html", "paired_cells.csv"]):
    safe_ticker_component(experiment_id, max_len=80)
    root = EXPERIMENTS_DIR.resolve()
    path = (EXPERIMENTS_DIR / experiment_id / file_name).resolve()
    if not path.is_relative_to(root) or not path.is_file():
        raise HTTPException(status_code=404, detail="Experiment output not found.")
    media_type = "text/html" if file_name.endswith(".html") else "text/csv"
    return FileResponse(path, media_type=media_type, filename=file_name)


FRONTEND_DIST = ROOT / "frontend" / "dist"
if FRONTEND_DIST.is_dir():
    assets_dir = FRONTEND_DIST / "assets"
    if assets_dir.is_dir():
        app.mount("/assets", StaticFiles(directory=assets_dir), name="frontend-assets")

    @app.get("/{frontend_path:path}", include_in_schema=False)
    def frontend(frontend_path: str):
        requested = (FRONTEND_DIST / frontend_path).resolve()
        if requested.is_relative_to(FRONTEND_DIST.resolve()) and requested.is_file():
            return FileResponse(requested)
        return FileResponse(FRONTEND_DIST / "index.html")
