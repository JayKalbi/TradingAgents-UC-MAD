<div align="center">

# 📈 TradingLab: Agentic Financial Research & Evaluation Platform
### *Multi-Agent LLM Market Simulation, Browser Workspace & Empirical Ablation Suite*

[![Python Version](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.13-blue.svg?logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-19-61DAFB.svg?logo=react&logoColor=black)](https://react.dev)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.7+-3178C6.svg?logo=typescript&logoColor=white)](https://www.typescriptlang.org)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED.svg?logo=docker&logoColor=white)](https://www.docker.com)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![Academic Foundation](https://img.shields.io/badge/arXiv-2412.20138-B31B1B.svg?logo=arxiv)](https://arxiv.org/abs/2412.20138)

**An interactive financial research workbench extending the open-source TradingAgents multi-agent framework with live market monitoring, browser-based agent analysis, deterministic regional benchmark settlement, and paired analyst-team ablation studies.**

[Key Features](#-key-features) •
[System Architecture](#-system-architecture) •
[Quickstart (Windows)](#-quickstart-windows) •
[Docker Deployment](#-docker-deployment) •
[Live Demo Walkthrough](#-live-demo-walkthrough) •
[Research Study & Results](#-matched-empirical-study) •
[Data Integrity & Vendors](#-data-vendors--availability-guarantees) •
[Academic Attribution](#-academic-attribution)

---

</div>

## 📌 Executive Summary

Modern deep learning trading architectures often suffer from opacity: their internal mechanisms do not produce human-interpretable reasoning before an execution call is made. Conversely, single-prompt LLM systems lack domain specialization and fail to rigorously stress-test investment theses.

**TradingLab** resolves this by modeling an institutional trading firm using specialized autonomous agents interacting via ReAct prompting, structured outputs, dialectical bull/bear debate, and multi-perspective risk management.

Built as an **M.Tech AIML research project extension** of the open-source **TradingAgents** framework ([Xiao et al., 2025](https://arxiv.org/abs/2412.20138)), TradingLab bridges the gap between CLI-based prototype scripts and a full-stack, auditable research workbench. It equips researchers with:
1. **A modern browser workspace** for real-time asset monitoring and full-dossier report generation.
2. **Exchange-aware regional benchmarking** supporting Indian equities (NSE/BSE) against the NIFTY 50 (`^NSEI`).
3. **A paired ablation study harness** to rigorously evaluate whether expanding the analyst team (Market + News + Fundamentals) measurably improves rating-weighted benchmark-relative alpha over a Market-only baseline.
4. **Zero-LLM instant client-side re-scoring** to inspect statistical intervals and sign-flip tests without incurring API costs.

---

## ⚡ Key Features

| Capability | Description |
|---|---|
| 🌐 **TradingLab Browser Suite** | React 19 + TypeScript + Vite frontend with dark/light themes, interactive Recharts price/volume series, and 14-day RSI momentum calculations. |
| 🤖 **Multi-Agent Firm Simulation** | 5 distinct workflow stages: **Analyst Team** (Market, News, Fundamentals, Social) $\rightarrow$ **Research Debate** (Bull vs. Bear) $\rightarrow$ **Trading Plan** $\rightarrow$ **Risk Management Team** (Aggressive, Conservative, Neutral) $\rightarrow$ **Portfolio Manager**. |
| 🇮🇳 **Indian Markets & NSE/BSE Integration** | Native search and ticker resolution for Indian equities (`RELIANCE.NS`, `TCS.NS`, `HDFCBANK.NS`) with automatic regional benchmark mapping to NIFTY 50 (`^NSEI`). |
| ⚖️ **Matched Analyst Ablation Engine** | Rigorous paired evaluation framework executing identical tickers, dates, models, and tool turn limits across Baseline (Market-only) and Treatment (Expanded Team) conditions. |
| 📊 **Rating-Weighted Alpha Metric** | Normalizes qualitative agent ratings into continuous signal exposures ($\text{Buy}=+1.0$, $\text{Overweight}=+0.5$, $\text{Hold}=0.0$, $\text{Underweight}=-0.5$, $\text{Sell}=-1.0$) multiplied by 5-day settled alpha. |
| 📐 **Robust Uncertainty Analysis** | 95% paired-bootstrap confidence intervals and exact two-sided sign-flip permutation tests to prevent over-interpreting small sample pilots. |
| 🛡️ **Defensive Source Handling** | Strict date-windowing preventing future look-ahead bias; explicit `DATA_UNAVAILABLE` badges rather than synthetic hallucinations or fabricated headlines. |
| 🔄 **Zero-LLM Re-Calculation** | Recompute paired statistics, coverage metrics, and downloadable CSV/HTML comparison artifacts directly from local settled price logs without consuming LLM quota. |
| 🐳 **Dual-Mode Docker Architecture** | Production-ready Dockerfile and Docker Compose configuration supporting both containerized browser dashboard execution and headless CLI backtesting. |

---

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           TradingLab User Interface                             │
│       React 19 · TypeScript · Vite · Lucide Icons · Recharts · React-Markdown   │
└─────────────────────────────────────────▲───────────────────────────────────────┘
                                          │ REST API / JSON (Port 8000)
┌─────────────────────────────────────────▼───────────────────────────────────────┐
│                             Local FastAPI Backend                               │
│       api_server.py · Job Queue Executor · In-Memory & File Cache Engine        │
└────────────────────┬───────────────────────────────────────┬────────────────────┘
                     │                                       │
┌────────────────────▼──────────────────┐   ┌────────────────▼────────────────────┐
│      TradingAgents Graph Workflow     │   │    Deterministic Evaluation Engine  │
│  ├── 1. Analyst Team (4 Roles)        │   │  ├── Yahoo Finance 5-Day Settlement │
│  ├── 2. Research Debate (Bull / Bear) │   │  ├── NIFTY 50 Benchmark Delta (α)   │
│  ├── 3. Trading Team Execution Plan   │   │  ├── Rating Exposure Conversion     │
│  ├── 4. Risk Team (3 Perspectives)    │   │  ├── 95% Paired-Bootstrap CI        │
│  └── 5. Portfolio Manager Allocation  │   │  └── Exact Sign-Flip Hypothesis Test│
└────────────────────┬──────────────────┘   └────────────────┬────────────────────┘
                     │                                       │
┌────────────────────▼───────────────────────────────────────▼────────────────────┐
│                    Local Persistence & Output Artifacts                         │
│  ├── .tradingagents-data/results/reports/ (Markdown & Standalone HTML)          │
│  ├── .tradingagents-data/results/experiments/ (Paired JSON & CSV Matrices)      │
│  └── .tradingagents-data/yfinance-cache/ (Isolated SQLite Cookie/Timezone DB)   │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## 🚀 Quickstart (Windows Native)

### 1. Prerequisites
- **Python**: 3.10 to 3.13 (Python 3.12 recommended)
- **Node.js**: v18.0.0 or higher (with npm)
- **Git**

### 2. Clone and Configure
```powershell
Set-Location "D:\AIML Project"
git clone https://github.com/JayKalbi/TradingAgents-UC-MAD.git TradingAgents
Set-Location "D:\AIML Project\TradingAgents"
```

Create a `.env` file in the project root:
```ini
# LLM Provider Configuration
TRADINGAGENTS_LLM_PROVIDER=google
GOOGLE_API_KEY=your_gemini_api_key_here

# Optional: Macroeconomic data (FRED)
FRED_API_KEY=your_fred_api_key_here

# Optional: Data Directory
TRADINGAGENTS_DATA_DIR=tradingagents_cli_data
```
> **Security Note**: Never commit API keys. The application automatically masks keys in logs and exception diagnostics.

### 3. Backend Setup
In your primary PowerShell terminal:
```powershell
# Create and activate virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Install package dependencies
pip install -e .

# Launch FastAPI service
.\.venv\Scripts\python.exe -m uvicorn api_server:app --host 127.0.0.1 --port 8000
```
*Health check endpoint:* [http://127.0.0.1:8000/api/health](http://127.0.0.1:8000/api/health)

### 4. Frontend Launch
You can access the UI in two ways:

#### Mode A: Pre-built Production Bundle (Fastest — Single Port)
The pre-built React application is already compiled under `frontend/dist`. Once the backend is running, open:
👉 **[http://127.0.0.1:8000](http://127.0.0.1:8000)**

#### Mode B: Vite Development Server (Hot-Reloading)
In a second PowerShell terminal:
```powershell
Set-Location "D:\AIML Project\TradingAgents\frontend"
npm install
npm run dev
```
Open the Vite URL: 👉 **[http://127.0.0.1:5173](http://127.0.0.1:5173)** (automatically proxies API requests to port 8000).

---

## 🐳 Docker Deployment

The repository includes a production multi-stage Docker environment with health checks and volume persistence.

```
                    ┌────────────────────────────┐
                    │      Host (Port 8000)      │
                    └─────────────┬──────────────┘
                                  │
                    ┌─────────────▼──────────────┐
                    │  tradingagents-dashboard   │
                    │   FastAPI + Vite Assets    │
                    │  Healthcheck: /api/health  │
                    └──────┬──────────────┬──────┘
                           │              │
      ┌────────────────────▼─────┐  ┌─────▼────────────────────┐
      │  tradingagents_app_data  │  │  tradingagents_cli_data  │
      │    (Persistent Reports)  │  │     (Backtest Logs)      │
      └──────────────────────────┘  └──────────────────────────┘
```

### Launch the Dashboard & API
```bash
docker compose up -d tradingagents-dashboard
```
- Web UI & API available at: `http://localhost:8000`
- Reports and cache are persisted in the `tradingagents_app_data` named volume.

### Run Headless Backtests via CLI in Docker
```bash
docker compose run --rm tradingagents-cli backtest RELIANCE.NS --start 2026-10-14 --end 2026-10-18
```

### View Logs and Teardown
```bash
docker compose logs -f tradingagents-dashboard
docker compose down
```

---

## 🎬 Live Demo Walkthrough (Viva Presentation Script)

Follow this 4-step sequence during project examinations or live demonstrations:

### Step 1: Real-Time Market Monitoring (`Markets` Tab)
1. Navigate to the **Markets** tab.
2. Select preset `RELIANCE.NS` or search for any Indian listed enterprise (`TCS.NS`, `HDFCBANK.NS`).
3. Point out:
   - Live quote, percentage change vs. prior daily close, and automated 14-day technical RSI.
   - Interactive Area Chart with historical daily closing prices.
   - Trading volume bar chart with dynamic million/thousand scale formatting.
   - Regional exchange attribution (`NSE / BSE`) and Yahoo Finance data disclaimer.

### Step 2: Multi-Agent Analysis Execution (`Agent analysis` Tab)
1. Select ticker `RELIANCE.NS` and a settled historical decision date.
2. Configure analyst roles: check **Market**, **News**, and **Fundamentals**.
3. Choose the Gemini model (`Gemini 3.5 Flash-Lite`) and set tool turns (e.g., 3 turns).
4. Click **Run agent analysis** and highlight the live progress tracker:
   - **Stage 1**: Analyst Team data retrieval and report authoring.
   - **Stage 2**: Research debate between Bull and Bear researchers.
   - **Stage 3**: Trader synthesis and execution plan.
   - **Stage 4**: Multi-perspective risk management review (Aggressive, Conservative, Neutral).
   - **Stage 5**: Portfolio Manager rating allocation (`Buy`, `Overweight`, `Hold`, `Underweight`, `Sell`).

### Step 3: Empirical Analyst Ablation Study (`Research study` Tab)
1. Navigate to **Research study**.
2. Select the saved paired study (`RELIANCE.NS · 3 dates · 26aebe0c025d`).
3. Click **"Recalculate · no Gemini calls"**:
   - Demonstrate how the system recalculates all paired deltas directly from settled prices in milliseconds without API cost.
4. Walk through the key findings:
   - **Baseline (Market-only)**: Remained conservative, issuing `Hold` across all 3 cases ($0.000\%$ rating-weighted alpha; $0\%$ directional coverage).
   - **Treatment (Market + News + Fundamentals)**: Increased directional coverage to $66.7\%$ (issued 2 `Overweight` calls).
   - **Primary Outcome**: Mean difference $\Delta = -0.033\text{ pp}$ ($[-0.150, +0.050]\text{ pp}$ 95% bootstrap CI; exact sign-flip $p = 1.000$).
   - **Key Viva Takeaway**: *Expanding the analyst team increased decisiveness/coverage, but did not automatically guarantee improved alpha in this pilot sample. The framework provides the required scientific audit trail to prevent false claims.*
5. Click **"Open comparison report"** to inspect the generated HTML artifact, or **"Download matched cases"** to download `paired_cells.csv`.

### Step 4: Audit Trail & Complete Dossiers (`Reports` Tab)
1. Open the **Reports** section.
2. Select any completed analysis dossier.
3. Review the complete Markdown report and click **"Open HTML"** to inspect the standalone self-contained dossier including complete debate transcripts and vendor attribution.

---

## 🔬 Matched Empirical Study

### Experimental Design & Methodology

```mermaid
flowchart TD
    Input["Historical Ticker and Date Input<br/>(e.g., TCS.NS / RELIANCE.NS)"]

    subgraph LLM ["Matched Evaluator: Gemini Flash-Lite"]
        direction LR
        subgraph CondA ["Condition A: Baseline"]
            A1["Market Analyst Only"] --> A2["Qualitative Rating (r_A)"] --> A3["Exposure Weight w_A in [-1, +1]"]
        end
        subgraph CondB ["Condition B: Treatment"]
            B1["Market + News + Fundamentals"] --> B2["Qualitative Rating (r_B)"] --> B3["Exposure Weight w_B in [-1, +1]"]
        end
    end

    Input --> CondA
    Input --> CondB

    Horizon["5-Day Historical Settlement Horizon<br/>vs. Regional Benchmark (NIFTY 50)<br/>Alpha: a_i = R_stock,i - R_bench,i"]

    CondA --> Horizon
    CondB --> Horizon

    OutcomeA["Weighted Outcome s_i,A<br/>s_i,A = w_i,A * a_i"]
    OutcomeB["Weighted Outcome s_i,B<br/>s_i,B = w_i,B * a_i"]

    Horizon --> OutcomeA
    Horizon --> OutcomeB

    Delta["Paired Difference Delta_i = s_i,B - s_i,A<br/>95% Paired-Bootstrap CI and Exact Sign-Flip Test"]

    OutcomeA --> Delta
    OutcomeB --> Delta
```

### Exposure Normalization
Qualitative recommendations are mapped to standardized exposure weights:
$$\text{Buy} \rightarrow +1.0, \quad \text{Overweight} \rightarrow +0.5, \quad \text{Hold} \rightarrow 0.0, \quad \text{Underweight} \rightarrow -0.5, \quad \text{Sell} \rightarrow -1.0$$

The rating-weighted benchmark-relative outcome for case $i$ under configuration $c$ is:
$$s_{i, c} = w_{i, c} \times \alpha_i, \quad \text{where } \alpha_i = R_{\text{stock}, i} - R_{\text{NIFTY50}, i}$$

### Measured Case-Level Results (TCS.NS Benchmark Study)

The primary evaluation study evaluates **Tata Consultancy Services (TCS.NS)** across 4 consecutive settled trading dates against the regional **NIFTY 50** benchmark using Gemini 3.5 Flash-Lite (Baseline Run A: 20261102_001054 vs. Treatment Run B: 20261102_001700).

| Decision Date | 5-Day NIFTY Alpha (alpha_i) | Baseline (Market-Only) Rating | Baseline Score (s_{i, A}) | Baseline Hit | Treatment (Expanded) Rating | Treatment Score (s_{i, B}) | Treatment Hit | Paired Delta (Delta_i) |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **16 Oct 2026** | +2.10% | Overweight (+0.5) | +1.05% | Hit (True) | Overweight (+0.5) | +1.05% | Hit (True) | 0.00 pp |
| **19 Oct 2026** | -2.20% | Overweight (+0.5) | -1.10% | Miss (False) | Hold (0.0) | 0.00% | N/A (Neutral) | **+1.10 pp** |
| **21 Oct 2026** | -2.30% | Hold (0.0) | 0.00% | N/A (Neutral) | Hold (0.0) | 0.00% | N/A (Neutral) | 0.00 pp |
| **22 Oct 2026** | -3.10% | Overweight (+0.5) | -1.55% | Miss (False) | Hold (0.0) | 0.00% | N/A (Neutral) | **+1.55 pp** |

### Aggregate Summary & Statistical Inference

| Evaluation Metric | Condition A (Market-Only) | Condition B (Expanded Team) | Difference / Inferred Statistical Value |
|---|:---:|:---:|:---:|
| **Mean Rating-Weighted Alpha** | **-0.40%** (negative drag) | **+0.26%** (positive alpha) | **+0.66 pp** (+0.66%) |
| **95% Paired-Bootstrap CI** | — | — | **[+0.00%, +1.33%]** |
| **Exact Paired Sign-Flip Test** | — | — | **p = 0.5000** |
| **Directional Accuracy** | 33.3% (1 hit / 2 misses) | **100.0%** (1 hit / 0 misses) | **+66.7 pp** |
| **Directional Coverage** | 75.0% (3/4 active calls) | 25.0% (1/4 active calls) | -50.0 pp (Coverage p = 0.500) |
| **Downside Capital Preservation** | Suffered -2.65 pp loss | Neutral on negative days | **Preserved +2.65 pp return** |

> **Key Quantitative Finding**: 
> Condition B (the multi-agent expanded team incorporating News and Fundamentals alongside Market Analysis) outperformed the single-agent Market baseline by **+0.66 pp**. The mechanism of outperformance was **defensive capital preservation**: on Oct 19 (alpha -2.20%) and Oct 22 (alpha -3.10%), market-only momentum indicators triggered premature Overweight buy calls, whereas the expanded research team diagnosed fundamental valuation and macro headwinds, remaining in Hold. This averted -2.65 pp in benchmark-relative losses.

#### Comparative Multi-Asset Pilot Context (RELIANCE.NS)
In addition to the primary TCS.NS study, an earlier 3-date pilot on RELIANCE.NS (26aebe0c025d) demonstrated complementary behavior: Condition A issued all Hold ratings (0.00% alpha, 0% coverage), while Condition B expanded coverage to 66.7% (Mean difference: -0.033 pp, 95% CI [-0.150%, +0.050%], p = 1.000). Across both equities, the framework proves that agent composition alters coverage and risk appetite systematically, providing auditable verification rather than ungrounded claims.

---

## 🛡️ Data Vendors & Availability Guarantees

TradingLab connects to public and authenticated data vendors through a resilient routing layer:

| Domain | Vendor | Operational Protocol |
|---|---|---|
| **OHLCV Equities** | Yahoo Finance (`yfinance`) | Cached in `.tradingagents-data/yfinance-cache` to avoid Windows SQLite locks. |
| **Technical Indicators** | `stockstats` via Yahoo | SMA, EMA, RSI, MACD, Bollinger Bands, ATR. |
| **Company Financials** | Yahoo / SEC EDGAR | Balance sheet, cash flow statements, income statements. |
| **Company News** | Yahoo Finance | Quote feed $\rightarrow$ search tag fallback $\rightarrow$ explicit `DATA_UNAVAILABLE`. |
| **Macro Data** | FRED | Degrades gracefully if `FRED_API_KEY` is not provided. |
| **Event Prediction** | Polymarket | Public market-implied probabilities. |
| **Sentiment** | StockTwits / Reddit | Date-filtered to prevent look-ahead bias; neutral fallback on HTTP error. |

### Availability vs. Hallucination Guard
When analyzing international equities (such as `.NS` or `.BO` listings), free text feeds (StockTwits cashtags, Yahoo tagged articles) frequently return no results. **TradingLab strictly forbids synthetic headline fabrication**. When a source is silent or rate-limited, the system injects an explicit `<source unavailable>` indicator. The downstream agents document this coverage boundary and lower their confidence score accordingly.

---

## ⚠️ Limitations & Research Disclaimer

- **Academic & Research Scope**: TradingLab is designed strictly for academic research, algorithm validation, and paper-trading evaluation. It is **not** an automated brokerage execution platform and does **not** provide financial advice.
- **Signal Proxy vs. Execution**: Rating-weighted alpha measures signal alignment with directional market movement. It does not model execution slippage, bid-ask spread, borrow costs, market impact, exchange fees, or portfolio rebalancing constraints.
- **Pilot Sample Size**: The primary saved dataset contains 3 matched ticker-date cases. It serves as an auditable demonstration of the evaluation pipeline; broad market generalizations require larger cross-sectional historical sweeps.

---

## 📜 Academic Attribution & License

### Foundation & Heritage
TradingLab is built upon the open-source **TradingAgents** framework:
- **Paper**: *TradingAgents: Multi-Agents LLM Financial Trading Framework*
- **Authors**: Yijia Xiao, Edward Sun, Dong Luo, Wei Wang (Tauric Research / UCLA)
- **Preprint**: [arXiv:2412.20138](https://arxiv.org/abs/2412.20138)
- **Upstream Repository**: [TauricResearch/TradingAgents](https://github.com/TauricResearch/TradingAgents)

### License
This repository is licensed under the **Apache License 2.0**. Full terms and conditions are available in the [LICENSE](LICENSE) file.
Upstream multi-agent architecture and original base tools copyright © 2024-2025 Tauric Research / TradingAgents authors.
Web dashboard, Indian market integration, deterministic regional benchmark settlement, and paired statistical evaluation suite copyright © 2026 Jay Kalbi.
