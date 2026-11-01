# TradingLab · Agentic Financial Research Platform

An interactive multi-agent financial research dashboard and empirical evaluation workbench extending the open-source **TradingAgents** framework.

Designed for financial research, paper-trading exploration, and empirical analyst-team ablation experiments.

---

## Overview & Academic Attribution

This repository contains an M.Tech project extension built on top of the open-source foundation **TradingAgents** (developed by Yijia Xiao, Edward Sun, Dong Luo, and Wei Wang; see [arXiv:2412.20138](https://arxiv.org/abs/2412.20138)). The original upstream framework introduced the core ReAct multi-agent trading firm simulation (analysts, bull/bear researchers, trader, risk management team, and portfolio manager).

### Project-Specific Research & Engineering Contributions
- **Interactive Browser Workspace (`TradingLab`)**: A modern React 19 + TypeScript frontend paired with a local FastAPI asynchronous service layer (`api_server.py`) for live market tracking, agent analysis execution, and report inspection.
- **Matched Analyst-Team Ablation Study**: A paired experimental harness comparing single-analyst (Market-only baseline) vs. multi-analyst (Market + News + Fundamentals) configurations under matched conditions on Indian equities (`RELIANCE.NS`, `TCS.NS`, etc.).
- **Deterministic Historical Settlement**: Evaluation of agent recommendations over a 5-trading-day settlement window against regional benchmarks (e.g. NIFTY 50 `^NSEI`), using rating-weighted benchmark-relative alpha.
- **Uncertainty & Significance Analysis**: Paired bootstrap confidence intervals and exact sign-flip testing.
- **Zero-LLM Re-scoring**: Capability to recompute all statistical metrics, tables, and comparison artifacts from saved backtest logs without incurring additional LLM quota or external API calls.
- **Full Containerization**: Dual-mode Docker support providing isolated services for both the browser dashboard/API and the original interactive CLI.

---

## Architecture & Workflow

```
┌────────────────────────────────────────────────────────┐
│             React + TypeScript Dashboard               │
│    (Market Monitor · Agent Analysis · Research Study)  │
└───────────────────────────▲────────────────────────────┘
                            │ REST / JSON (port 8000)
┌───────────────────────────▼────────────────────────────┐
│               Local FastAPI Service                    │
│    (api_server.py · Job Queue · Cache Management)      │
└─────────────┬────────────────────────────┬─────────────┘
              │                            │
   ┌──────────▼───────────┐     ┌──────────▼───────────┐
   │  TradingAgents Graph │     │  Deterministic Eval  │
   │  - Market Analyst    │     │  - NIFTY 50 Benchmark│
   │  - News Analyst      │     │  - 5-Day Alpha Settle│
   │  - Fundamentals      │     │  - Rating Exposure   │
   │  - Bull / Bear Debates│    │  - Bootstrap CI &    │
   │  - Trader & Risk Mgmt│     │    Exact Sign-Flip   │
   └──────────┬───────────┘     └──────────┬───────────┘
              │                            │
   ┌──────────▼────────────────────────────▼───────────┐
   │ Local Storage (.tradingagents-data / results_dir)  │
   └───────────────────────────────────────────────────┘
```

---

## Prerequisites & Configuration

### Requirements
- **Python**: 3.10+ (tested with Python 3.12 / 3.13)
- **Node.js & npm**: Node 18+ (tested with Node 20/22, npm 10+)
- **Docker & Docker Compose**: Optional, for containerized execution
- **API Keys**: Required only for running *new* LLM analyses. Re-scoring existing experiments, viewing market data, and inspecting reports requires no LLM API key.

### Configuration (`.env`)
Create a `.env` file in the repository root:
```ini
# Primary LLM provider (default: google)
TRADINGAGENTS_LLM_PROVIDER=google
GOOGLE_API_KEY=your_gemini_api_key_here

# Optional: FRED macro data key (if unconfigured, macro indicators degrade gracefully)
FRED_API_KEY=your_fred_api_key_here

# Optional data directory override
TRADINGAGENTS_DATA_DIR=tradingagents_cli_data
```
> **Security Notice**: Never commit `.env` or paste live API keys into public logs. The local API server automatically masks detected API keys in error diagnostics.

---

## Setup & Running Locally

### Option 1: Native Windows Setup

#### 1. Python Environment
In PowerShell:
```powershell
Set-Location "D:\AIML Project\TradingAgents"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .
```

#### 2. Start the FastAPI Server
Run from a standard PowerShell terminal (avoid restricted sandbox terminals to prevent socket permission errors `WinError 10013`):
```powershell
Set-Location "D:\AIML Project\TradingAgents"
.\.venv\Scripts\python.exe -m uvicorn api_server:app --host 127.0.0.1 --port 8000
```
Verify the API health check at [http://127.0.0.1:8000/api/health](http://127.0.0.1:8000/api/health).

#### 3. Start the React Frontend
In a second terminal:
```powershell
Set-Location "D:\AIML Project\TradingAgents\frontend"
npm install
npm run dev
```
Open [http://127.0.0.1:5173](http://127.0.0.1:5173). The Vite dev server proxies API calls to `127.0.0.1:8000`.

To serve the pre-built static frontend directly from FastAPI on port 8000:
```powershell
Set-Location "D:\AIML Project\TradingAgents\frontend"
npm run build
Set-Location "D:\AIML Project\TradingAgents"
.\.venv\Scripts\python.exe -m uvicorn api_server:app --host 127.0.0.1 --port 8000
```
Then open [http://127.0.0.1:8000](http://127.0.0.1:8000).

---

### Option 2: Docker & Docker Compose

The environment includes multi-service Compose configuration for both the browser dashboard/API and the interactive CLI.

#### Launching the Web Dashboard
```bash
docker compose up -d tradingagents-dashboard
```
- Web dashboard & API: `http://localhost:8000`
- Application data and logs are persisted across restarts in the `tradingagents_app_data` named volume.
- Includes container health checks polling `/api/health`.

#### Launching the CLI Workflow
```bash
docker compose run --rm tradingagents-cli
```
Or use the backwards-compatible upstream service name:
```bash
docker compose run --rm tradingagents
```

#### Checking Logs & Stopping
```bash
docker compose logs -f tradingagents-dashboard
docker compose down
```

---

## Live Demo Walkthrough (Presentation Script)

For project demonstrations and viva examinations, follow this 4-step sequence:

### 1. Market Monitor (`Markets` tab)
- Navigate to the **Markets** page.
- Select preset `RELIANCE.NS` or search for Indian equities (`TCS.NS`, `HDFCBANK.NS`).
- Demonstrate live / delayed price series, daily volume charts, 14-day RSI momentum calculations, and the NIFTY 50 benchmark mapping.

### 2. Multi-Agent Analysis (`Agent analysis` tab)
- Navigate to **Agent analysis**.
- Select ticker `RELIANCE.NS` and a settled decision date.
- Choose analyst roles (Market, News, Fundamentals, Social).
- Observe the 5-stage sequential execution: Analyst Team $\rightarrow$ Research Debate $\rightarrow$ Trading Plan $\rightarrow$ Risk Review $\rightarrow$ Portfolio Decision.
- Note how missing or untagged news feeds are surfaced with explicit vendor coverage indicators rather than hallucinated headlines.

### 3. Matched Research Study (`Research study` tab)
- Navigate to **Research study**.
- View the pre-loaded 3-case pilot comparison (`RELIANCE.NS` across October 14, 15, and 16, 2026).
- Click **"Recalculate · no Gemini calls"** to demonstrate instant client-side statistical re-scoring from saved backtest logs.
- Explain the key evaluation metrics:
  - **Rating-weighted alpha**: Exposure mapping (Buy $+1.0$, Overweight $+0.5$, Hold $0.0$, Underweight $-0.5$, Sell $-1.0$) multiplied by 5-day NIFTY-relative alpha.
  - **Directional coverage vs. Accuracy**: Expanding the analyst team increased coverage from $0\%$ (Hold in all 3 baseline cases) to $66.7\%$ (2 Overweight recommendations in the treatment condition).
  - **Statistical interpretation**: Mean difference $-0.033$ percentage points, 95% bootstrap CI $[-0.150, +0.050]$ pp, exact sign-flip $p = 1.000$. Demonstrate why a small pilot does not establish superiority, but provides an auditable evaluation pipeline.
- Click **"Open comparison report"** to inspect the generated HTML comparison artifact, and **"Download matched cases"** to inspect `paired_cells.csv`.

### 4. Audit & Saved Reports (`Reports` tab)
- Open the **Reports** section to inspect generated Markdown dossiers and standalone HTML reports containing complete debate transcripts, risk reviews, and data vendor notices.

---

## Data Vendors & Source Handling

| Domain | Default Vendor | Fallback / Behavior |
|---|---|---|
| OHLCV Prices | Yahoo Finance (`yfinance`) | Cached in `.tradingagents-data/yfinance-cache` |
| Indicators | Yahoo Finance (`yfinance`) | Computed via `stockstats` |
| Fundamentals | Yahoo Finance (`yfinance`) | Balance sheet, cash flow, income statement |
| Company News | Yahoo Finance (`yfinance`) | Quote feed $\rightarrow$ search tag fallback $\rightarrow$ explicit vendor unavailable indicator |
| Macro Indicators | FRED | Gracefully degrades if `FRED_API_KEY` is not configured |
| Prediction Markets | Polymarket | Public market-implied probabilities |
| Sentiment / Social | StockTwits / Reddit | Scraped live with strict date-bounding; neutral fallback on HTTP error |

> **News & Sentiment Availability Note**: Unlike US large-cap equities (e.g. `AAPL`), Yahoo Finance does not maintain dedicated news ticker tags for most non-US listings (such as NSE equities ending in `.NS`). Furthermore, social media platforms (Reddit, StockTwits) frequently exhibit zero discussions for regional tickers or require unauthenticated endpoints subject to HTTP rate limits. TradingLab explicitly captures these vendor responses as `DATA_UNAVAILABLE` rather than hallucinating stories or manufacturing sentiment.

---

## Troubleshooting & FAQ

1. **Windows `[WinError 10013] An attempt was made to access a socket in a way forbidden by its access permissions`**:
   - This occurs when launching Python from restricted IDE sandbox terminals.
   - **Fix**: Launch `uvicorn` from a standard administrative or user PowerShell terminal.
2. **`Yahoo Finance cache could not be opened`**:
   - TradingLab isolates SQLite cache files under `.tradingagents-data/yfinance-cache` to prevent Windows profile permission collisions. Ensure the project folder has write permissions.
3. **Reports list is empty in the dashboard**:
   - Saved reports are stored in `.tradingagents-data/results/reports/`. Complete an analysis in the dashboard or run `tradingagents backtest` to generate reports.

---

## Limitations & Research Disclaimer

- **Research & Educational Software**: This system is designed solely for academic research and paper-trading evaluation. It does not execute live market orders or manage real-money brokerage capital.
- **Signal Proxy, Not Execution Simulation**: Rating-weighted benchmark-relative alpha is a theoretical signal evaluation proxy. It does not account for bid-ask spread, market impact, slippage, liquidity, exchange transaction fees, or position sizing constraints.
- **Exploratory Pilot Sample**: The saved paired study contains 3 matched ticker-date cases. While statistically valid for demonstrating the evaluation pipeline, broader empirical claims require larger multi-asset cross-sectional sweeps.
- **Third-Party Data Reliability**: Market quotes and news items are fetched from free/public APIs and may be delayed or unavailable.

---

## License

This project is licensed under the Apache License 2.0. See [LICENSE](LICENSE) for details. Upstream multi-agent architecture and base tools copyright © 2024-2025 Tauric Research / TradingAgents authors.
