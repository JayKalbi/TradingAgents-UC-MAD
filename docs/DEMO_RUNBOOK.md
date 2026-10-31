# Demo and viva runbook

## Clean-start commands (PowerShell)

Terminal 1 — API backend, from repository root:

    Set-Location "D:\AIML Project\TradingAgents"
    .\.venv\Scripts\python.exe -m uvicorn api_server:app --host 127.0.0.1 --port 8000

Terminal 2 — React frontend:

    Set-Location "D:\AIML Project\TradingAgents\frontend"
    npm run dev

Open the Vite URL printed in Terminal 2, normally http://127.0.0.1:5173. Keep both terminals open. The project does not place live orders.

## Demo sequence

1. Markets: load RELIANCE.NS; show quote, date/time, price history, and volume. Explain Yahoo Finance data can be delayed or unavailable.
2. Agent analysis: select RELIANCE.NS, a past analysis date, market/news/fundamentals, Gemini 3.5 Flash-Lite, and a low tool-turn setting. State that a live run depends on Gemini API quota and external data access.
3. Reports: open the saved RELIANCE.NS report. Point out model/run metadata, the source-availability section, and that unavailable news does not mean there was no news.
4. Research study: select the saved experiment and use Recalculate — no Gemini calls. Show the three matched cases, per-case paired chart, weighted alpha, interval, p-value, and coverage.
5. Explain that the three-case result is a pilot only; do not describe it as a reliable finding or investment signal.

## Research result in one minute

The question is whether adding news and fundamentals analysts changes rating-weighted NIFTY-relative outcomes compared with a market-only analyst. The saved sample contains three matched RELIANCE.NS dates. A averaged 0.000% weighted alpha and B averaged -0.033%; B minus A was -0.033 percentage points with a 95% interval from -0.150 to +0.050 and exact paired sign-flip p=1.000. A issued Hold on all three cases; B issued two Overweight calls and one Hold. This sample cannot support a general conclusion.

## Likely viva questions

- Why compare matched dates? Matching holds the ticker, date, market outcome, and model family constant so the main planned difference is analyst composition.
- Why rating-weighted alpha? It makes recommendation direction and realized benchmark-relative outcome explicit, while remaining a simple signal proxy.
- Why is this not portfolio performance? It excludes trading costs, slippage, capital constraints, sizing, and execution.
- What does p=1.000 mean? The observed three paired differences do not provide evidence against the null under the exact sign-flip procedure; it does not prove the systems are equivalent.
- Why is baseline directional accuracy N/A? The market-only configuration returned Hold for all three cases; neutral recommendations are excluded from directional accuracy.
- What is the project contribution beyond upstream code? The local application workflow, matched India experiment and rescoring, paired reporting, visual comparison, and explicit source-coverage disclosure. Preserve upstream attribution.
- What are the main limitations? Three cases, one company, one model, short date window, no repeated stochastic runs, incomplete source snapshots, and simplified outcome proxy.

