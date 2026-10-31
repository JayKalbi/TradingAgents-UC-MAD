# Project completion status — 30 October 2026

## Integrated project

TradingAgents is the single project for AIML and ADAP. The React/TypeScript dashboard, local FastAPI service, global market monitoring, agent-analysis workflow, saved reports, and India-focused paired experiment are implemented. The dashboard includes price-history and volume charts, and the experiment view compares matched alpha outcomes visually.

## Research question and design

Question: Does adding news and fundamentals analysts to a market-only analyst configuration change rating-weighted NIFTY-relative outcomes on matched Indian-equity decision cases?

Condition A: market analyst only.
Condition B: market, news, and fundamentals analysts.
Model: Gemini 3.5 Flash-Lite.
Ticker: RELIANCE.NS.
Dates: 2026-10-14, 2026-10-15, 2026-10-16.
Matched settled sample: n = 3.

## Measured pilot results

- Mean raw realized alpha was 0.233% in both conditions because both configurations share the same matched market outcomes.
- Mean rating-weighted alpha: A = 0.000%; B = -0.033%.
- Paired difference B minus A: -0.033 percentage points.
- Paired-bootstrap 95% interval: -0.150 to +0.050 percentage points.
- Exact paired sign-flip p-value: 1.000.
- Directional coverage: A = 0/3 (0%); B = 2/3 (66.7%).
- Directional accuracy: A is undefined (zero non-neutral calls); B = 1/2 (50%).
- No agent or settlement failures were recorded across the six analysis cells.

Interpretation: this is an exploratory three-case pilot. The result does not establish a winner, equivalence, or predictive performance. The current run is not enough for a strong research conclusion.

## What is done

1. End-to-end local product and multi-page React dashboard.
2. Global symbol-based market monitoring, with India as the showcased research market.
3. Paired outcome computation and saved experiment rescoring without additional Gemini calls.
4. Statistical summaries, matched-case export, HTML comparison report, and dashboard charts.
5. Reported source-availability notes distinguishing missing data from evidence of no event.
6. LaTeX research manuscript at research-paper/main.tex, using the attached TradingAgents paper as a layout reference (single-column article, centered title and author block, numbered sections, author-year citations). The manuscript now includes an end-to-end architecture figure, a paired-effect figure, case arithmetic, and a limitations-led discussion. It compiles with the Codex desktop compiler.
7. Demo and viva runbook at docs/DEMO_RUNBOOK.md. The analyst report now adds a cached price/SMA chart and reader guide; the React dashboard supports light and dark themes. The production frontend build succeeds.

## Remaining before submission

1. Expand the matched sample to several Indian companies and additional settled dates. Keep the same ticker/date cases in A and B, and retain failed/unavailable cases in the run log.
2. Confirm the Gemini project is on Free Tier in AI Studio before live runs. Google AI Pro is not itself Gemini API quota. Do not run if AI Studio shows a paid tier unless you explicitly accept the cost.
3. Recalculate the study from the saved experiment and freeze the metadata, paired CSV, plots, and model/settings before writing final claims.
4. Update the manuscript after expanding the sample, then add any institute-specific title-page details and verify its citation and disclosure requirements.
5. Rehearse a clean startup and demo. The dashboard needs live Yahoo Finance connectivity; the saved report and experiment artifacts are fallback evidence.
6. Export and visually inspect a final PDF before submission. The Codex desktop compiler confirms source compilation. Local MiKTeX export remains blocked by first-run setup/profile access and a missing local font package; no final manuscript PDF is included yet.

## Source and integrity notes

The codebase is adapted from the MIT-licensed TradingAgents project; keep its license and attribution. Cite the original paper and project. This manuscript reports the saved experiment rather than making up results. Similarity scores cannot be guaranteed; use the draft as a research record, revise it in your own words, and follow your institute's disclosure and citation rules.


