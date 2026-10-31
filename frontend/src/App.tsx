import { useEffect, useMemo, useState, type ReactNode } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import {
  Activity, ArrowDownRight, ArrowUpRight, BarChart3, BookOpen, BrainCircuit,
  Check, ChevronRight, CircleHelp, Clock3, Database, Download, Globe2,
  LayoutDashboard, LoaderCircle, RefreshCw, Search, ShieldCheck, Sparkles,
  TrendingUp, WalletCards, Wifi, X, Moon, Sun,
} from "lucide-react";
import {
  Area, AreaChart, Bar, BarChart, CartesianGrid, Legend, ReferenceLine,
  ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";
import { api, CompanySearchResult, experimentFileUrl, Job, MarketData, ReportSummary, reportHtmlUrl, SavedExperiment } from "./api";

type Page = "markets" | "analysis" | "research" | "reports";
type Health = { status: string; api_key_configured: boolean; default_model: string; market_data: string };

const presets = [
  { ticker: "^NSEI", name: "NIFTY 50", market: "India" },
  { ticker: "RELIANCE.NS", name: "Reliance Industries", market: "India" },
  { ticker: "TCS.NS", name: "Tata Consultancy Services", market: "India" },
  { ticker: "HDFCBANK.NS", name: "HDFC Bank", market: "India" },
  { ticker: "AAPL", name: "Apple", market: "United States" },
  { ticker: "MSFT", name: "Microsoft", market: "United States" },
  { ticker: "SAP.DE", name: "SAP", market: "Germany" },
  { ticker: "7203.T", name: "Toyota Motor", market: "Japan" },
  { ticker: "0700.HK", name: "Tencent", market: "Hong Kong" },
  { ticker: "BTC-USD", name: "Bitcoin", market: "Crypto" },
];

const modelOptions = [
  { id: "gemini-3.5-flash-lite", label: "Gemini 3.5 Flash-Lite · default" },
  { id: "gemini-3.1-flash-lite", label: "Gemini 3.1 Flash-Lite" },
];

const navItems: { id: Page; label: string; icon: typeof LayoutDashboard }[] = [
  { id: "markets", label: "Markets", icon: LayoutDashboard },
  { id: "analysis", label: "Agent analysis", icon: BrainCircuit },
  { id: "research", label: "Research study", icon: BarChart3 },
  { id: "reports", label: "Reports", icon: BookOpen },
];

function formatPrice(value: number, ticker: string) {
  const formatted = value.toLocaleString("en-IN", { maximumFractionDigits: 2, minimumFractionDigits: 2 });
  if (ticker.endsWith(".NS") || ticker.endsWith(".BO")) return `₹${formatted}`;
  return ticker.startsWith("^") ? formatted : formatted;
}

function formatPercent(value: number) {
  return `${value > 0 ? "+" : ""}${value.toFixed(2)}%`;
}

function App() {
  const [theme, setTheme] = useState<"light" | "dark">(() => {
    const saved = window.localStorage.getItem("tradingagents-theme");
    return saved === "dark" ? "dark" : "light";
  });
  const [page, setPage] = useState<Page>("markets");
  const [health, setHealth] = useState<Health | null>(null);
  const [marketTicker, setMarketTicker] = useState("RELIANCE.NS");
  const [marketData, setMarketData] = useState<MarketData | null>(null);
  const [marketLoading, setMarketLoading] = useState(false);
  const [marketError, setMarketError] = useState("");
  const [period, setPeriod] = useState("3mo");
  const [jobId, setJobId] = useState("");
  const [job, setJob] = useState<Job | null>(null);
  const [selectedReport, setSelectedReport] = useState("");
  const [reportMarkdown, setReportMarkdown] = useState("");
  const [reportList, setReportList] = useState<ReportSummary[]>([]);
  const [globalError, setGlobalError] = useState("");

  useEffect(() => {
    api.health().then(setHealth).catch(() => setHealth(null));
    void loadMarket("RELIANCE.NS", "3mo");
  }, []);

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    window.localStorage.setItem("tradingagents-theme", theme);
  }, [theme]);

  useEffect(() => {
    if (!jobId) return;
    let stopped = false;
    const poll = async () => {
      try {
        const next = await api.job(jobId);
        if (stopped) return;
        setJob(next);
        if (next.status === "completed" || next.status === "failed") {
          setJobId("");
          if (next.status === "completed" && next.kind === "analysis" && next.result) {
            const result = next.result as { report_id?: string };
            if (result.report_id) {
              setPage("reports");
              setSelectedReport(result.report_id);
              void loadReport(result.report_id);
              void loadReports();
            }
          }
          if (next.status === "completed" && next.kind === "experiment") setPage("research");
        }
      } catch (error) {
        if (!stopped) {
          setGlobalError(error instanceof Error ? error.message : "Could not retrieve job status.");
          setJobId("");
        }
      }
    };
    void poll();
    const timer = window.setInterval(() => void poll(), 1500);
    return () => { stopped = true; window.clearInterval(timer); };
  }, [jobId]);

  useEffect(() => {
    if (page === "reports") void loadReports();
  }, [page]);

  async function loadMarket(ticker: string, selectedPeriod = period) {
    setMarketLoading(true);
    setMarketError("");
    try {
      const data = await api.market(ticker, selectedPeriod);
      setMarketData(data);
      setMarketTicker(ticker.toUpperCase());
    } catch (error) {
      setMarketError(error instanceof Error ? error.message : "Could not load market data.");
    } finally {
      setMarketLoading(false);
    }
  }

  async function loadReports() {
    try {
      const reports = await api.reports();
      setReportList(reports);
      if (!selectedReport && reports[0]) {
        setSelectedReport(reports[0].id);
        await loadReport(reports[0].id);
      }
    } catch {
      setReportList([]);
    }
  }

  async function loadReport(id: string) {
    if (!id) return;
    try {
      const report = await api.report(id);
      setSelectedReport(id);
      setReportMarkdown(report.markdown);
    } catch (error) {
      setGlobalError(error instanceof Error ? error.message : "Could not load report.");
    }
  }

  const pageTitle = navItems.find((item) => item.id === page)?.label ?? "Markets";

  return (
    <div className="app-shell" data-theme={theme}>
      <aside className="sidebar">
        <button className="brand" onClick={() => setPage("markets")} aria-label="Go to markets">
          <span className="brand-mark"><Activity size={20} /></span>
          <span><strong>TRADELAB</strong><small>AGENTIC RESEARCH</small></span>
        </button>
        <div className="sidebar-label">WORKSPACE</div>
        <nav className="nav-list" aria-label="Main navigation">
          {navItems.map(({ id, label, icon: Icon }) => (
            <button key={id} className={`nav-item ${page === id ? "active" : ""}`} onClick={() => setPage(id)}>
              <Icon size={18} strokeWidth={1.8} /><span>{label}</span>{page === id && <ChevronRight size={15} className="nav-arrow" />}
            </button>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <div className="sidebar-note"><ShieldCheck size={16} /><span>Research mode<br /><small>No orders are placed</small></span></div>
          <div className="sidebar-version">TRADINGAGENTS · LOCAL</div>
        </div>
      </aside>

      <main className="main-area">
        <header className="topbar">
          <div className="breadcrumb"><span>Workspace</span><ChevronRight size={14} /><strong>{pageTitle}</strong></div>
          <div className="topbar-right">
            <button className="theme-toggle" onClick={() => setTheme(theme === "light" ? "dark" : "light")} aria-label={`Switch to ${theme === "light" ? "dark" : "light"} theme`} title={`Switch to ${theme === "light" ? "dark" : "light"} theme`} aria-pressed={theme === "dark"}>
              {theme === "light" ? <Moon size={16} /> : <Sun size={16} />}<span>{theme === "light" ? "Dark" : "Light"}</span>
            </button>
            <span className={`connection ${health ? "connected" : "disconnected"}`}><span className="connection-dot" />{health ? "Local API connected" : "API offline"}</span>
            <button className="icon-button" title="About this app" onClick={() => setGlobalError("TradingAgents is a research and paper-trading tool. It does not place live orders or provide financial advice.")}><CircleHelp size={18} /></button>
          </div>
        </header>

        {globalError && <div className="global-alert"><span>{globalError}</span><button onClick={() => setGlobalError("")} aria-label="Dismiss"><X size={16} /></button></div>}

        {page === "markets" && (
          <MarketsPage
            ticker={marketTicker} data={marketData} loading={marketLoading} error={marketError} period={period}
            onTicker={setMarketTicker} onPeriod={(next) => { setPeriod(next); void loadMarket(marketTicker, next); }}
            onLoad={() => void loadMarket(marketTicker)} onPreset={(ticker) => void loadMarket(ticker)}
          />
        )}
        {page === "analysis" && <AnalysisPage health={health} job={job?.kind === "analysis" ? job : null} busy={Boolean(jobId)} onStart={async (payload) => {
          setGlobalError("");
          try { const started = await api.startAnalysis(payload); setJobId(started.job_id); setJob({ id: started.job_id, kind: "analysis", status: "queued", progress: 0, message: "Queued", result: null, error: null }); }
          catch (error) { setGlobalError(error instanceof Error ? error.message : "Could not start analysis."); }
        }} />}
        {page === "research" && <ResearchPage health={health} job={job?.kind === "experiment" ? job : null} busy={Boolean(jobId)} onStart={async (payload) => {
          setGlobalError("");
          try { const started = await api.startExperiment(payload); setJobId(started.job_id); setJob({ id: started.job_id, kind: "experiment", status: "queued", progress: 0, message: "Queued", result: null, error: null }); }
          catch (error) { setGlobalError(error instanceof Error ? error.message : "Could not start experiment."); }
        }} />}
        {page === "reports" && <ReportsPage reports={reportList} selected={selectedReport} markdown={reportMarkdown} onSelect={loadReport} onRefresh={loadReports} />}
      </main>
    </div>
  );
}

function PageHeading({ eyebrow, title, description, action }: { eyebrow: string; title: string; description: string; action?: ReactNode }) {
  return <div className="page-heading"><div><div className="eyebrow">{eyebrow}</div><h1>{title}</h1><p>{description}</p></div>{action}</div>;
}

function MarketsPage({
  ticker, data, loading, error, period, onTicker, onPeriod, onLoad, onPreset,
}: {
  ticker: string; data: MarketData | null; loading: boolean; error: string; period: string;
  onTicker: (value: string) => void; onPeriod: (value: string) => void; onLoad: () => void; onPreset: (value: string) => void;
}) {
  const [draft, setDraft] = useState(ticker);
  useEffect(() => setDraft(ticker), [ticker]);
  const changeIsUp = (data?.change_pct ?? 0) >= 0;

  return (
    <div className="page-content">
      <PageHeading eyebrow="GLOBAL MARKET MONITOR" title="Market overview" description="Explore price history across Yahoo Finance-supported markets. Live quotes are best-effort and may be delayed." action={<div className="live-pill"><span />MARKET DATA</div>} />
      <section className="control-panel">
        <form className="ticker-search" onSubmit={(event) => { event.preventDefault(); onLoad(); }}>
          <Search size={18} />
          <input aria-label="Market ticker" value={draft} onChange={(event) => { setDraft(event.target.value); onTicker(event.target.value); }} placeholder="Ticker: RELIANCE.NS, AAPL, SAP.DE, 7203.T" />
          <button className="button button-primary" type="submit" disabled={loading}>{loading ? <LoaderCircle className="spin" size={16} /> : <Search size={16} />} Load market</button>
        </form>
        <div className="quick-picks">
          <span className="muted-label">QUICK SYMBOLS</span>
          {presets.map((item) => <button key={item.ticker} className={`symbol-chip ${ticker === item.ticker ? "selected" : ""}`} onClick={() => { setDraft(item.ticker); onPreset(item.ticker); }} title={`${item.name} · ${item.market}`}>{item.ticker}</button>)}
        </div>
      </section>

      {error && <div className="notice error-notice"><X size={17} />{error}</div>}
      {data && <>
        <div className="market-identity"><div className="identity-icon"><Globe2 size={20} /></div><div><strong>{data.ticker}</strong><span>{data.symbol} · {presets.find((item) => item.ticker === data.ticker)?.market ?? "Market selected by symbol"}</span></div><div className="identity-asof"><span className="mini-dot" />Latest available · {data.as_of.replace("T", " ").slice(0, 16)}</div><button className="button button-quiet refresh-button" onClick={onLoad} disabled={loading}><RefreshCw size={15} className={loading ? "spin" : ""} />Refresh</button></div>
        <div className="metric-grid">
          <MetricCard label="Latest quote" value={formatPrice(data.price, data.ticker)} note={data.source} icon={<WalletCards size={17} />} />
          <MetricCard label="Change vs. prior close" value={formatPercent(data.change_pct)} note="Latest quote compared with last daily close" icon={changeIsUp ? <ArrowUpRight size={17} /> : <ArrowDownRight size={17} />} positive={changeIsUp} negative={!changeIsUp} />
          <MetricCard label="14-day RSI" value={data.rsi_14 == null ? "—" : data.rsi_14.toFixed(1)} note="Technical momentum indicator" icon={<Activity size={17} />} />
          <MetricCard label="History window" value={period.toUpperCase()} note={`${data.bars.length} daily observations`} icon={<Clock3 size={17} />} />
        </div>
        <section className="panel chart-panel">
          <div className="panel-heading"><div><h2>Price history</h2><p>Daily close · sourced from Yahoo Finance</p></div><div className="period-toggle">{[["1mo", "1M"], ["3mo", "3M"], ["6mo", "6M"], ["1y", "1Y"]].map(([key, label]) => <button key={key} className={period === key ? "active" : ""} onClick={() => onPeriod(key)}>{label}</button>)}</div></div>
          <div className="chart-wrap">
            <ResponsiveContainer width="100%" height="100%"><AreaChart data={data.bars} margin={{ top: 12, right: 12, left: -14, bottom: 0 }}>
              <defs><linearGradient id="marketFill" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="var(--chart-line)" stopOpacity={0.24} /><stop offset="100%" stopColor="var(--chart-line)" stopOpacity={0} /></linearGradient></defs>
              <CartesianGrid stroke="var(--chart-grid)" strokeDasharray="3 5" vertical={false} />
              <XAxis dataKey="date" tickFormatter={(value: string) => value.slice(5)} tickLine={false} axisLine={false} tick={{ fill: "var(--chart-tick)", fontSize: 11 }} minTickGap={28} />
              <YAxis domain={["auto", "auto"]} tickLine={false} axisLine={false} tick={{ fill: "var(--chart-tick)", fontSize: 11 }} tickFormatter={(value: number) => value.toLocaleString("en-IN", { maximumFractionDigits: 0 })} />
              <Tooltip contentStyle={{ background: "var(--chart-tooltip)", border: "1px solid var(--chart-tooltip-border)", borderRadius: 10, color: "var(--chart-tooltip-text)" }} labelStyle={{ color: "var(--muted)" }} formatter={(value: number) => [formatPrice(value, data.ticker), "Close"]} />
              <Area type="monotone" dataKey="close" stroke="var(--chart-line)" strokeWidth={2.5} fill="url(#marketFill)" activeDot={{ r: 4, fill: "var(--chart-line)", stroke: "var(--panel)", strokeWidth: 2 }} />
            </AreaChart></ResponsiveContainer>
          </div>
          <div className="source-note"><Database size={14} />{data.disclaimer}</div>
        </section>
        <section className="panel chart-panel volume-panel">
          <div className="panel-heading"><div><h2>Trading volume</h2><p>Daily shares traded · sourced from Yahoo Finance</p></div><BarChart3 size={18} className="panel-icon" /></div>
          <div className="volume-chart-wrap"><ResponsiveContainer width="100%" height="100%"><BarChart data={data.bars} margin={{ top: 8, right: 12, left: -12, bottom: 0 }}>
            <CartesianGrid stroke="var(--chart-grid)" strokeDasharray="3 5" vertical={false} />
            <XAxis dataKey="date" tickFormatter={(value: string) => value.slice(5)} tickLine={false} axisLine={false} tick={{ fill: "var(--chart-tick)", fontSize: 10 }} minTickGap={28} />
            <YAxis tickLine={false} axisLine={false} tick={{ fill: "var(--chart-tick)", fontSize: 10 }} tickFormatter={(value: number) => value >= 1e6 ? `${(value / 1e6).toFixed(1)}M` : `${(value / 1e3).toFixed(0)}K`} />
            <Tooltip contentStyle={{ background: "var(--chart-tooltip)", border: "1px solid var(--chart-tooltip-border)", borderRadius: 10, color: "var(--chart-tooltip-text)" }} labelStyle={{ color: "var(--muted)" }} formatter={(value: number) => [value.toLocaleString("en-IN"), "Volume"]} />
            <Bar dataKey="volume" name="Volume" fill="var(--chart-volume)" radius={[3, 3, 0, 0]} />
          </BarChart></ResponsiveContainer></div>
          <div className="source-note"><Database size={14} />Volume may be missing or reported as zero for some instruments; check the source before interpreting it.</div>
        </section>
      </>}
      {!data && !loading && !error && <div className="empty-state"><TrendingUp size={26} /><h3>Choose a symbol to inspect</h3><p>Enter a Yahoo Finance ticker or start with an example above.</p></div>}
    </div>
  );
}

function MetricCard({ label, value, note, icon, positive, negative }: { label: string; value: string; note: string; icon: ReactNode; positive?: boolean; negative?: boolean }) {
  return <div className="metric-card"><div className="metric-label">{label}<span className="metric-icon">{icon}</span></div><strong className={positive ? "metric-positive" : negative ? "metric-negative" : ""}>{value}</strong><small>{note}</small></div>;
}

function AnalysisPage({ health, job, busy, onStart }: { health: Health | null; job: Job | null; busy: boolean; onStart: (payload: object) => Promise<void> }) {
  const [ticker, setTicker] = useState("RELIANCE.NS");
  const [analysisDate, setAnalysisDate] = useState(new Date().toISOString().slice(0, 10));
  const [analysts, setAnalysts] = useState<string[]>(["market", "news", "fundamentals"]);
  const [model, setModel] = useState("gemini-3.5-flash-lite");
  const [toolRounds, setToolRounds] = useState(3);
  const [submitted, setSubmitted] = useState(false);
  const isRunning = busy && job?.kind === "analysis";

  function toggleAnalyst(value: string) {
    setAnalysts((current) => current.includes(value) ? current.filter((item) => item !== value) : [...current, value]);
  }

  return <div className="page-content">
    <PageHeading eyebrow="LLM-POWERED WORKFLOW" title="Agent analysis" description="Run the existing multi-agent research workflow on any Yahoo Finance-supported asset. Results are for research and paper trading only." />
    <div className="analysis-layout">
      <section className="panel form-panel">
        <div className="panel-heading"><div><h2>Configure analysis</h2><p>One ticker per run · external API calls begin only after you press run.</p></div><BrainCircuit size={19} className="panel-icon" /></div>
        <form onSubmit={(event) => { event.preventDefault(); setSubmitted(true); void onStart({ ticker, analysis_date: analysisDate, analysts, model, max_tool_rounds: toolRounds }); }}>
          <label className="field-label" htmlFor="analysis-ticker">Ticker</label>
          <input id="analysis-ticker" className="text-input" value={ticker} onChange={(event) => setTicker(event.target.value.toUpperCase())} placeholder="RELIANCE.NS, AAPL, 7203.T, BTC-USD" required />
          <div className="form-hint">Global examples: <button type="button" onClick={() => setTicker("AAPL")}>AAPL</button><button type="button" onClick={() => setTicker("SAP.DE")}>SAP.DE</button><button type="button" onClick={() => setTicker("7203.T")}>7203.T</button><button type="button" onClick={() => setTicker("RELIANCE.NS")}>RELIANCE.NS</button></div>
          <label className="field-label" htmlFor="analysis-date">Analysis date</label>
          <input id="analysis-date" className="text-input" type="date" value={analysisDate} max={new Date().toISOString().slice(0, 10)} onChange={(event) => setAnalysisDate(event.target.value)} required />
          <div className="field-label analyst-label">Analyst roles</div>
          <div className="check-grid">{[
            ["market", "Market analyst", "Price action and technical indicators"],
            ["news", "News analyst", "Recent company and market news"],
            ["fundamentals", "Fundamentals", "Company financial data where available"],
            ["social", "Social sentiment", "Public social and sentiment sources"],
          ].map(([value, label, hint]) => <label key={value} className={`check-card ${analysts.includes(value) ? "checked" : ""}`}><input type="checkbox" checked={analysts.includes(value)} onChange={() => toggleAnalyst(value)} /><span className="check-visual">{analysts.includes(value) && <Check size={12} />}</span><span><strong>{label}</strong><small>{hint}</small></span></label>)}</div>
          <div className="form-row">
            <div><label className="field-label" htmlFor="model-select">Gemini model</label><select id="model-select" className="text-input" value={model} onChange={(event) => setModel(event.target.value)}>{modelOptions.map((item) => <option key={item.id} value={item.id}>{item.label}</option>)}</select></div>
            <div><label className="field-label" htmlFor="tool-rounds">Tool turns / agent</label><select id="tool-rounds" className="text-input" value={toolRounds} onChange={(event) => setToolRounds(Number(event.target.value))}>{[2, 3, 4, 5, 6].map((value) => <option key={value} value={value}>{value} turns</option>)}</select></div>
          </div>
          <div className="api-note"><Sparkles size={16} /><span>Gemini API usage follows your project’s tier and quota. This dashboard never enables paid billing; check Google AI Studio usage and tier before larger runs.</span></div>
          {!health?.api_key_configured && <div className="notice error-notice"><X size={16} />GOOGLE_API_KEY is not configured in the repository .env file.</div>}
          <button className="button button-primary run-button" type="submit" disabled={busy || !health?.api_key_configured || analysts.length === 0}>{isRunning ? <LoaderCircle size={17} className="spin" /> : <BrainCircuit size={17} />}{isRunning ? "Analysis running…" : "Run agent analysis"}</button>
        </form>
      </section>
      <aside className="right-stack">
        <div className="panel info-panel"><div className="section-kicker">WHAT RUNS</div><h3>One analysis, five workflow stages</h3><ol className="workflow-list"><li><span>01</span> Analyst team</li><li><span>02</span> Research debate</li><li><span>03</span> Trading plan</li><li><span>04</span> Risk review</li><li><span>05</span> Portfolio decision</li></ol><p>Changing analyst roles controls stage one. The existing downstream decision and risk workflow remains intact.</p></div>
        <div className="panel info-panel"><div className="section-kicker">DATA COVERAGE</div><h3>Global symbols, exchange-aware benchmarks</h3><p>Use Yahoo Finance symbols with their exchange suffix. Indian equities such as <code>RELIANCE.NS</code> use NIFTY 50 as the benchmark in the built-in evaluation path.</p><div className="source-note"><Wifi size={14} />Yahoo Finance data may be delayed or unavailable.</div></div>
      </aside>
    </div>
    {isRunning && <JobProgress job={job!} />}
    {job?.kind === "analysis" && job.status === "failed" && <div className="notice error-notice"><X size={17} />{job.error ?? "The analysis failed."}</div>}
    {submitted && job?.kind === "analysis" && job.status === "completed" && job.result && <div className="notice success-notice"><Check size={17} />Analysis complete. Final rating: <strong>{String(job.result.rating ?? "Review")}</strong>. Report saved in the Reports section.</div>}
  </div>;
}

function ResearchPage({ health, job, busy, onStart }: { health: Health | null; job: Job | null; busy: boolean; onStart: (payload: object) => Promise<void> }) {
  const [tickersText, setTickersText] = useState("RELIANCE.NS");
  const [companyQuery, setCompanyQuery] = useState("");
  const [companyResults, setCompanyResults] = useState<CompanySearchResult[]>([]);
  const [companySearchLoading, setCompanySearchLoading] = useState(false);
  const [companySearchError, setCompanySearchError] = useState("");
  const [dates, setDates] = useState<string[]>([]);
  const [dateOptions, setDateOptions] = useState<string[]>([]);
  const [loadingDates, setLoadingDates] = useState(false);
  const [model, setModel] = useState("gemini-3.5-flash-lite");
  const [toolRounds, setToolRounds] = useState(3);
  const [savedExperiments, setSavedExperiments] = useState<SavedExperiment[]>([]);
  const [selectedSavedExperiment, setSelectedSavedExperiment] = useState("");
  const [savedExperimentLoading, setSavedExperimentLoading] = useState(true);
  const [recalculateBusy, setRecalculateBusy] = useState(false);
  const [recalculateError, setRecalculateError] = useState("");
  const [recalculatedResult, setRecalculatedResult] = useState<Record<string, unknown> | null>(null);
  const tickers = useMemo(() => tickersText.split(",").map((value) => value.trim().toUpperCase()).filter(Boolean), [tickersText]);
  const caseCount = tickers.length * dates.length;
  const isRunning = busy && job?.kind === "experiment";
  const result = job?.kind === "experiment" && job.status === "completed" ? job.result as Record<string, unknown> | null : null;
  const displayedResult = recalculatedResult ?? result;

  useEffect(() => {
    let active = true;
    api.savedExperiments().then((saved) => {
      if (!active) return;
      setSavedExperiments(saved);
      setSelectedSavedExperiment((current) => current || saved[0]?.id || "");
    }).catch((error) => {
      if (active) setRecalculateError(error instanceof Error ? error.message : "Could not load saved experiments.");
    }).finally(() => { if (active) setSavedExperimentLoading(false); });
    return () => { active = false; };
  }, []);

  useEffect(() => {
    const query = companyQuery.trim();
    if (query.length < 2) { setCompanyResults([]); setCompanySearchError(""); setCompanySearchLoading(false); return; }
    let active = true;
    const timer = window.setTimeout(() => {
      setCompanySearchLoading(true);
      setCompanySearchError("");
      api.searchIndianCompanies(query).then((data) => {
        if (active) setCompanyResults(data.results);
      }).catch((error) => {
        if (active) { setCompanyResults([]); setCompanySearchError(error instanceof Error ? error.message : "Company search failed."); }
      }).finally(() => { if (active) setCompanySearchLoading(false); });
    }, 350);
    return () => { active = false; window.clearTimeout(timer); };
  }, [companyQuery]);

  useEffect(() => {
    let active = true;
    const timer = window.setTimeout(() => {
      setLoadingDates(true);
      Promise.all(tickers.slice(0, 4).map((ticker) => api.market(ticker, "6mo"))).then((markets) => {
        if (!active) return;
        const common = markets.reduce((dates, market) => dates.filter((value) => market.settled_dates.includes(value)), markets[0]?.settled_dates ?? []);
        const available = common.slice(-24).reverse();
        setDateOptions(available);
        setDates((current) => current.length ? current.filter((value) => available.includes(value)) : available.slice(0, 1));
      }).catch(() => { if (active) { setDateOptions([]); setDates([]); } }).finally(() => { if (active) setLoadingDates(false); });
    }, 300);
    return () => { active = false; window.clearTimeout(timer); };
  }, [tickers.join(",")]);

  const toggleDate = (value: string) => setDates((current) => current.includes(value) ? current.filter((item) => item !== value) : [...current, value].sort());
  const addCompany = (company: CompanySearchResult) => {
    setTickersText((current) => [...new Set([...current.split(",").map((item) => item.trim().toUpperCase()).filter(Boolean), company.symbol])].join(", "));
    setCompanyQuery("");
    setCompanyResults([]);
  };

  return <div className="page-content">
    <PageHeading eyebrow="AIML RESEARCH STUDY" title="Analyst composition experiment" description="A matched historical comparison using Indian equities and the project's NIFTY benchmark mapping." />
    <section className="research-question"><div className="question-icon"><Sparkles size={19} /></div><div><div className="section-kicker">RESEARCH QUESTION</div><h2>How does analyst-team composition affect rating-weighted benchmark-relative outcomes?</h2><p>Independent variable: analyst-team composition. Primary outcome: five-trading-day NIFTY-relative alpha multiplied by a normalized agent rating exposure. The same ticker, date, model, and limits are used in both conditions.</p></div></section>
    <div className="research-layout">
      <section className="panel form-panel">
        <div className="panel-heading"><div><h2>Matched backtest setup</h2><p>India is the experimental market; other markets remain available in Market Monitor and Agent Analysis.</p></div><BarChart3 size={18} className="panel-icon" /></div>
        <label className="field-label" htmlFor="company-search">Search Indian listed companies</label>
        <div className="company-search-wrap">
          <div className="company-search-input"><Search size={15} /><input id="company-search" value={companyQuery} onChange={(event) => setCompanyQuery(event.target.value)} placeholder="Search company name or ticker, e.g. Infosys" /><span>{companySearchLoading ? "Searching…" : "NSE / BSE"}</span></div>
          {companyQuery.trim().length >= 2 && !companySearchLoading && !companySearchError && <div className="company-search-results">{companyResults.length ? companyResults.map((company) => <button type="button" key={company.symbol} onClick={() => addCompany(company)}><span><strong>{company.name}</strong><small>{company.exchange}</small></span><code>{company.symbol}</code><span className="add-company">Add</span></button>) : <div className="company-no-results">No Indian listing found. You can enter its Yahoo symbol below.</div>}</div>}
        </div>
        {companySearchError && <div className="form-hint error-text">{companySearchError}</div>}
        <label className="field-label" htmlFor="experiment-tickers">Selected Indian companies / symbols</label>
        <input id="experiment-tickers" className="text-input" value={tickersText} onChange={(event) => setTickersText(event.target.value)} placeholder="RELIANCE.NS, TCS.NS, HDFCBANK.NS" />
        <div className="form-hint">Add companies from search or enter Yahoo symbols directly. The India experiment accepts NSE (.NS) and BSE (.BO) listings, up to four per run.</div>
        <div className="date-heading"><label className="field-label">Settled historical dates</label><span>{loadingDates ? "Loading NSE trading dates…" : `${dates.length} selected`}</span></div>
        <div className="date-picker-grid">{dateOptions.length ? dateOptions.map((value) => <label key={value} className={`date-chip ${dates.includes(value) ? "selected" : ""}`}><input type="checkbox" checked={dates.includes(value)} onChange={() => toggleDate(value)} />{value}</label>) : <div className="date-empty">Historical dates load from Yahoo Finance. If unavailable, check market connectivity and refresh.</div>}</div>
        <div className="form-row">
          <div><label className="field-label" htmlFor="experiment-model">Gemini model</label><select id="experiment-model" className="text-input" value={model} onChange={(event) => setModel(event.target.value)}>{modelOptions.map((item) => <option key={item.id} value={item.id}>{item.label}</option>)}</select></div>
          <div><label className="field-label" htmlFor="experiment-rounds">Tool turns / agent</label><select id="experiment-rounds" className="text-input" value={toolRounds} onChange={(event) => setToolRounds(Number(event.target.value))}>{[2, 3, 4, 5, 6].map((value) => <option key={value} value={value}>{value} turns</option>)}</select></div>
        </div>
        <div className="experiment-conditions"><div><span className="condition-tag baseline">A · BASELINE</span><strong>Market analyst</strong><small>One analyst role</small></div><div className="condition-arrow">→</div><div><span className="condition-tag treatment">B · TREATMENT</span><strong>Market + news + fundamentals</strong><small>Three analyst roles</small></div></div>
        <div className="notice warning-notice"><CircleHelp size={17} /><span><strong>Quota and sample note.</strong> Each ticker-date case runs both conditions through the LLM workflow. Start with a small pilot. One or two matched cases check the pipeline but are too small for strong statistical claims.</span></div>
        {!health?.api_key_configured && <div className="notice error-notice"><X size={16} />GOOGLE_API_KEY is not configured in .env.</div>}
        <button className="button button-primary run-button" disabled={busy || !health?.api_key_configured || !tickers.length || !dates.length || tickers.length > 4 || dates.length > 6} onClick={() => { setRecalculatedResult(null); void onStart({ tickers, dates, model, max_tool_rounds: toolRounds }); }}>
          {isRunning ? <LoaderCircle size={17} className="spin" /> : <BarChart3 size={17} />}{isRunning ? "Experiment running…" : `Run matched pilot · ${caseCount * 2} analysis cases`}
        </button>
      </section>
      <aside className="right-stack">
        <div className="panel info-panel"><div className="section-kicker">MEASUREMENTS</div><h3>Paired outcomes</h3><ul className="measure-list"><li><span>Primary metric</span><strong>Rating-weighted NIFTY-relative alpha</strong></li><li><span>Uncertainty</span><strong>Paired bootstrap 95% interval</strong></li><li><span>Paired test</span><strong>Sign-flip test</strong></li><li><span>Benchmark</span><strong>NIFTY 50 (^NSEI)</strong></li></ul><p>Rating weights are Buy +1, Overweight +0.5, Hold 0, Underweight −0.5, Sell −1. This is a research proxy, not simulated portfolio execution. Indian listed equities with <code>.NS</code> or <code>.BO</code> symbols use regional benchmarks.</p></div>
        <div className="panel info-panel"><div className="section-kicker">INTERPRETATION</div><h3>Do not assume the expanded team wins</h3><p>A negative, near-zero, or uncertain result is still a valid finding. Report the observed results, sample size, model version, run settings, and the limits of this short experiment.</p></div>
      </aside>
    </div>
    <section className="panel saved-experiment-panel">
      <div className="panel-heading"><div><div className="section-kicker">SAVED RESULTS</div><h2>Re-score an existing experiment</h2><p>Recalculates rating-weighted alpha, directional accuracy, and coverage from saved backtest logs. No Gemini calls are made.</p></div><RefreshCw size={18} className="panel-icon" /></div>
      {savedExperimentLoading ? <div className="form-hint">Loading saved experiment history…</div> : savedExperiments.length ? <div className="saved-experiment-controls">
        <select className="text-input" aria-label="Choose saved experiment" value={selectedSavedExperiment} onChange={(event) => { setSelectedSavedExperiment(event.target.value); setRecalculatedResult(null); setRecalculateError(""); }}>
          {savedExperiments.map((saved) => <option key={saved.id} value={saved.id}>{saved.tickers.join(", ")} · {saved.dates.length} dates · {saved.id}</option>)}
        </select>
        <button className="button button-secondary" disabled={recalculateBusy || !selectedSavedExperiment} onClick={async () => {
          setRecalculateBusy(true); setRecalculateError(""); setRecalculatedResult(null);
          try { setRecalculatedResult(await api.recalculateExperiment(selectedSavedExperiment)); }
          catch (error) { setRecalculateError(error instanceof Error ? error.message : "Could not recalculate the saved experiment."); }
          finally { setRecalculateBusy(false); }
        }}>{recalculateBusy ? <LoaderCircle size={15} className="spin" /> : <RefreshCw size={15} />}{recalculateBusy ? "Re-scoring saved runs…" : "Recalculate · no Gemini calls"}</button>
      </div> : <div className="form-hint">No saved paired experiments found yet.</div>}
      {recalculateError && <div className="notice error-notice"><X size={16} />{recalculateError}</div>}
    </section>
    {isRunning && <JobProgress job={job!} />}
    {job?.kind === "experiment" && job.status === "failed" && <div className="notice error-notice"><X size={17} />{job.error ?? "The experiment failed."}</div>}
    {displayedResult && <ExperimentResults result={displayedResult} />}
  </div>;
}

function JobProgress({ job }: { job: Job }) {
  return <div className="panel progress-panel"><div className="progress-top"><div><div className="section-kicker">{job.kind === "experiment" ? "EXPERIMENT PROGRESS" : "AGENT WORKFLOW"}</div><strong>{job.message}</strong></div><span>{job.kind === "experiment" ? `${job.progress}%` : <LoaderCircle size={17} className="spin" />}</span></div>{job.kind === "experiment" && <div className="progress-track"><span style={{ width: `${job.progress}%` }} /></div>}<p>{job.kind === "analysis" ? "The multi-agent workflow can take a few minutes. Keep this browser tab and the local API terminal open." : "Backtest cases run one at a time. Avoid closing the API terminal until the comparison is saved."}</p></div>;
}

function ExperimentResults({ result }: { result: Record<string, unknown> }) {
  const cells = (result.cells ?? []) as Array<Record<string, unknown>>;
  const experimentId = String(result.experiment_id ?? "");
  const meanDelta = Number(result.mean_delta ?? 0) * 100;
  const pct = (value: unknown) => typeof value === "number" ? `${(value * 100).toFixed(1)}%` : "N/A";
  const pp = (value: unknown) => typeof value === "number" ? `${(value * 100).toFixed(1)} pp` : "N/A";
  const hit = (value: unknown) => value === true ? "Hit" : value === false ? "Miss" : "Neutral / flat";
  return <section className="panel results-panel">
    <div className="panel-heading"><div><div className="section-kicker">MEASURED RESULT</div><h2>Paired experiment complete</h2><p>{String(result.model)} · {String(result.matched_cases)} matched settled ticker-date cases</p></div><span className="result-tag"><Check size={14} />SAVED</span></div>
    <div className="metric-grid result-metrics">
      <MetricCard label="Rating-weighted α · market-only" value={`${(Number(result.mean_rating_alpha_baseline ?? 0) * 100).toFixed(2)}%`} note="Signal-weighted NIFTY-relative outcome" icon={<Activity size={16} />} />
      <MetricCard label="Rating-weighted α · expanded" value={`${(Number(result.mean_rating_alpha_expanded ?? 0) * 100).toFixed(2)}%`} note="Signal-weighted NIFTY-relative outcome" icon={<Activity size={16} />} />
      <MetricCard label="Mean difference · B − A" value={`${meanDelta > 0 ? "+" : ""}${meanDelta.toFixed(2)} pp`} note={`95% interval ${(Number(result.ci_low ?? 0) * 100).toFixed(2)}% to ${(Number(result.ci_high ?? 0) * 100).toFixed(2)}%`} icon={<TrendingUp size={16} />} positive={meanDelta > 0} negative={meanDelta < 0} />
      <MetricCard label="Paired test p-value" value={Number(result.p_value ?? 1).toFixed(4)} note={String(result.test_method ?? "Paired sign-flip")} icon={<BarChart3 size={16} />} />
      <MetricCard label="Directional accuracy · A / B" value={`${pct(result.directional_accuracy_baseline)} / ${pct(result.directional_accuracy_expanded)}`} note={`Directional calls n=${Number(result.directional_cases_baseline ?? 0)} / ${Number(result.directional_cases_expanded ?? 0)}`} icon={<Check size={16} />} />
      <MetricCard label="Directional coverage · A / B" value={`${pct(result.directional_coverage_baseline)} / ${pct(result.directional_coverage_expanded)}`} note="Share of matched cases with a non-neutral rating" icon={<Activity size={16} />} />
      <MetricCard label="Paired accuracy change · B − A" value={pp(result.paired_accuracy_delta)} note={`${Number(result.paired_directional_cases ?? 0)} shared directional cases · p=${typeof result.accuracy_p_value === "number" ? result.accuracy_p_value.toFixed(3) : "N/A"}`} icon={<TrendingUp size={16} />} positive={Number(result.paired_accuracy_delta) > 0} negative={Number(result.paired_accuracy_delta) < 0} />
    </div>
    {cells.length > 0 && <section className="panel experiment-chart-panel">
      <div className="panel-heading"><div><h3>Paired outcome by case</h3><p>Rating-weighted benchmark-relative alpha · each bar is one matched ticker/date</p></div><BarChart3 size={18} className="panel-icon" /></div>
      <div className="experiment-chart-wrap"><ResponsiveContainer width="100%" height="100%"><BarChart data={cells.map((cell) => ({ ...cell, caseLabel: `${String(cell.ticker).replace(/\.NS$|\.BO$/, "")} · ${String(cell.date).slice(5)}`, baseline: Number(cell.baseline_rating_alpha ?? 0) * 100, expanded: Number(cell.expanded_rating_alpha ?? 0) * 100 }))} margin={{ top: 8, right: 10, left: -12, bottom: 12 }}>
        <CartesianGrid stroke="var(--chart-grid)" strokeDasharray="3 5" vertical={false} />
        <XAxis dataKey="caseLabel" tickLine={false} axisLine={false} tick={{ fill: "var(--chart-tick)", fontSize: 10 }} interval={0} angle={-18} textAnchor="end" height={48} />
        <YAxis tickLine={false} axisLine={false} tick={{ fill: "var(--chart-tick)", fontSize: 10 }} tickFormatter={(value: number) => `${value.toFixed(1)}%`} />
        <ReferenceLine y={0} stroke="var(--muted)" />
        <Tooltip contentStyle={{ background: "var(--chart-tooltip)", border: "1px solid var(--chart-tooltip-border)", borderRadius: 10, color: "var(--chart-tooltip-text)" }} formatter={(value: number) => [`${value.toFixed(2)}%`, ""]} />
        <Legend />
        <Bar dataKey="baseline" name="Market-only" fill="var(--chart-volume)" radius={[3, 3, 0, 0]} />
        <Bar dataKey="expanded" name="Expanded analyst team" fill="var(--chart-line)" radius={[3, 3, 0, 0]} />
      </BarChart></ResponsiveContainer></div>
    </section>}
    {cells.length > 0 && <div className="table-wrap"><table><thead><tr><th>Ticker</th><th>Decision date</th><th>Outcome α</th><th>Rating A</th><th>Hit A</th><th>Weighted α A</th><th>Rating B</th><th>Hit B</th><th>Weighted α B</th><th>Δ weighted α</th></tr></thead><tbody>{cells.map((cell) => <tr key={`${cell.ticker}-${cell.date}`}><td>{String(cell.ticker)}</td><td>{String(cell.date)}</td><td>{(Number(cell.baseline_alpha) * 100).toFixed(1)}%</td><td>{String(cell.baseline_rating)}</td><td>{hit(cell.baseline_direction_correct)}</td><td>{(Number(cell.baseline_rating_alpha) * 100).toFixed(1)}%</td><td>{String(cell.expanded_rating)}</td><td>{hit(cell.expanded_direction_correct)}</td><td>{(Number(cell.expanded_rating_alpha) * 100).toFixed(1)}%</td><td>{(Number(cell.rating_alpha_delta) * 100).toFixed(1)} pp</td></tr>)}</tbody></table></div>}
    <div className="notice warning-notice"><CircleHelp size={16} /><span>Directional accuracy excludes Hold ratings and zero rounded alpha; coverage is shown separately. Realized alpha is the same market outcome for both agents. Rating-weighted alpha uses normalized weights (Buy +1, Overweight +0.5, Hold 0, Underweight −0.5, Sell −1): a signal proxy, not a portfolio execution simulation. Small samples are exploratory.</span></div>
    {experimentId && <div className="download-row"><a className="button button-secondary" href={experimentFileUrl(experimentId, "comparison.html")} target="_blank" rel="noreferrer"><BarChart3 size={15} />Open comparison report</a><a className="button button-quiet" href={experimentFileUrl(experimentId, "paired_cells.csv")}><Download size={15} />Download matched cases</a></div>}
  </section>;
}

function ReportsPage({ reports, selected, markdown, onSelect, onRefresh }: { reports: ReportSummary[]; selected: string; markdown: string; onSelect: (id: string) => void; onRefresh: () => void }) {
  const current = reports.find((report) => report.id === selected);
  return <div className="page-content">
    <PageHeading eyebrow="RUN HISTORY" title="Research reports" description="Review and export completed agent analyses. Reports include model, analyst, date, and data-source metadata." action={<button className="button button-quiet" onClick={onRefresh}><RefreshCw size={15} />Refresh list</button>} />
    <div className="reports-layout">
      <aside className="panel report-list"><div className="panel-heading"><div><h2>Saved runs</h2><p>{reports.length} report{reports.length === 1 ? "" : "s"}</p></div><BookOpen size={18} className="panel-icon" /></div>{reports.length ? reports.map((report) => <button key={report.id} className={`report-row ${selected === report.id ? "selected" : ""}`} onClick={() => onSelect(report.id)}><span className="report-row-icon"><BarChart3 size={16} /></span><span><strong>{report.title.replace("Trading Analysis Report: ", "")}</strong><small>{report.metadata.slice(0, 2).join(" · ")}</small></span><ChevronRight size={15} /></button>) : <div className="list-empty">No reports yet. Complete an agent analysis to save the first one.</div>}</aside>
      <section className="panel report-view">{current ? <><div className="panel-heading"><div><h2>{current.title}</h2><p>{current.metadata.slice(0, 3).join(" · ")}</p></div>{current.has_html && <a className="button button-secondary" href={reportHtmlUrl(current.id)} target="_blank" rel="noreferrer"><Download size={15} />Open HTML</a>}</div><div className="report-markdown"><ReactMarkdown remarkPlugins={[remarkGfm]}>{markdown}</ReactMarkdown></div></> : <div className="empty-state"><BookOpen size={28} /><h3>Reports appear here after a completed run</h3><p>The app saves a Markdown report and standalone HTML page for each analysis.</p></div>}</section>
    </div>
  </div>;
}

export default App;
