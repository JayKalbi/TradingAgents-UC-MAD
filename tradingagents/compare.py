"""Paired statistical comparison of two TradingAgents backtest runs.

Backtest cells are independent recommendations, not portfolio trades. This
module compares settled benchmark-relative alpha for the same ticker/date cells
across two runs and writes an auditable HTML and CSV report.
"""

from __future__ import annotations

import csv
import html
import itertools
import random
from dataclasses import dataclass
from pathlib import Path

from tradingagents.agents.rating import RATING_REVIEW
from tradingagents.dataflows.symbols import safe_ticker_component
from tradingagents.memory import TradingMemoryLog

_BOOTSTRAP_SAMPLES = 10_000
_PERMUTATION_SAMPLES = 20_000
_EXACT_PERMUTATION_LIMIT = 20

# Active exposure relative to the regional benchmark. This maps the five
# recommendation levels to a transparent, normalized research proxy; it is
# not an order simulator or a claim about actual portfolio sizing.
_RATING_WEIGHT = {
    "Buy": 1.0,
    "Overweight": 0.5,
    "Hold": 0.0,
    "Underweight": -0.5,
    "Sell": -1.0,
}


def _format_percent(value: float | None, digits: int = 2) -> str:
    return "N/A" if value is None else f"{value:.{digits}%}"


@dataclass(frozen=True)
class PairedCell:
    ticker: str
    date: str
    rating_a: str
    alpha_a: float
    rating_b: str
    alpha_b: float

    @property
    def delta(self) -> float:
        """Difference in realized alpha (B − A), independent of the agent rating."""
        return self.alpha_b - self.alpha_a

    @property
    def rating_alpha_a(self) -> float:
        return _RATING_WEIGHT.get(self.rating_a, 0.0) * self.alpha_a

    @property
    def rating_alpha_b(self) -> float:
        return _RATING_WEIGHT.get(self.rating_b, 0.0) * self.alpha_b

    @property
    def rating_delta(self) -> float:
        """Difference in rating-weighted benchmark-relative outcome (B − A)."""
        return self.rating_alpha_b - self.rating_alpha_a

    @property
    def directional_correct_a(self) -> bool | None:
        return _directional_correct(self.rating_a, self.alpha_a)

    @property
    def directional_correct_b(self) -> bool | None:
        return _directional_correct(self.rating_b, self.alpha_b)

    @property
    def coverage_delta(self) -> float:
        return float(_RATING_WEIGHT.get(self.rating_b, 0.0) != 0) - float(
            _RATING_WEIGHT.get(self.rating_a, 0.0) != 0
        )


def _directional_correct(rating: str, alpha: float) -> bool | None:
    """Whether a non-neutral rating matched the sign of realized alpha."""
    weight = _RATING_WEIGHT.get(rating, 0.0)
    if weight == 0 or alpha == 0:
        return None
    return (weight > 0) == (alpha > 0)


@dataclass(frozen=True)
class BacktestComparison:
    run_a: str
    run_b: str
    cells: tuple[PairedCell, ...]
    unmatched_a: int
    unmatched_b: int
    mean_alpha_a: float
    mean_alpha_b: float
    mean_delta: float
    ci_low: float
    ci_high: float
    p_value: float
    test_method: str
    mean_rating_alpha_a: float
    mean_rating_alpha_b: float
    mean_rating_delta: float
    rating_ci_low: float
    rating_ci_high: float
    rating_p_value: float
    rating_test_method: str
    directional_accuracy_a: float | None
    directional_accuracy_b: float | None
    directional_cases_a: int
    directional_cases_b: int
    directional_coverage_a: float
    directional_coverage_b: float
    paired_directional_cases: int
    paired_accuracy_delta: float | None
    accuracy_ci_low: float | None
    accuracy_ci_high: float | None
    accuracy_p_value: float | None
    coverage_delta: float
    coverage_ci_low: float
    coverage_ci_high: float
    coverage_p_value: float

    def render(self) -> str:
        return "\n".join([
            f"Paired backtest comparison: {self.run_a} vs {self.run_b}",
            f"Matched settled cells: {len(self.cells)}",
            f"Unmatched settled cells: A={self.unmatched_a}, B={self.unmatched_b}",
            f"Mean realized alpha (market outcome): A {self.mean_alpha_a:+.2%} · B {self.mean_alpha_b:+.2%}",
            f"Mean rating-weighted alpha: A {self.mean_rating_alpha_a:+.2%} · B {self.mean_rating_alpha_b:+.2%}",
            f"Mean paired rating-weighted difference (B − A): {self.mean_rating_delta:+.2%}",
            f"95% paired-bootstrap CI: [{self.rating_ci_low:+.2%}, {self.rating_ci_high:+.2%}]",
            f"Two-sided paired sign-flip test: p={self.rating_p_value:.4g} ({self.rating_test_method})",
            f"Directional accuracy: A {_format_percent(self.directional_accuracy_a)} (n={self.directional_cases_a}) · B {_format_percent(self.directional_accuracy_b)} (n={self.directional_cases_b})",
            f"Directional coverage: A {self.directional_coverage_a:.2%} · B {self.directional_coverage_b:.2%} · difference {self.coverage_delta:+.2%}",
            "Alpha is rounded to 0.1 percentage points in the source logs; "
            "text feeds are not archived. The test assumes sign symmetry under the null; "
            "overlapping holding windows can make cells dependent. Treat small-sample results as exploratory.",
        ])


def _read_cells(results_dir: Path, run_id: str) -> dict[tuple[str, str], tuple[str, float]]:
    """Read settled, scored cells for a run, rejecting unsafe or ambiguous ids."""
    safe_id = safe_ticker_component(run_id, max_len=80)
    log_path = results_dir / "backtest" / safe_id / "trading_memory.md"
    if not log_path.is_file():
        raise FileNotFoundError(f"no backtest memory log for run {run_id!r}: {log_path}")

    entries = TradingMemoryLog({"memory_log_path": str(log_path)}).load_entries()
    cells: dict[tuple[str, str], tuple[str, float]] = {}
    for entry in entries:
        if entry.get("pending") or entry.get("rating") == RATING_REVIEW:
            continue
        try:
            alpha = float((entry.get("alpha") or "").strip().rstrip("%")) / 100
        except ValueError:
            continue
        key = (entry["ticker"], entry["date"])
        if key in cells:
            raise ValueError(f"run {run_id!r} contains duplicate settled cell {key[0]} {key[1]}")
        cells[key] = (entry["rating"], alpha)
    return cells


def _percentile(sorted_values: list[float], probability: float) -> float:
    """Linear-interpolated percentile for an already sorted sequence."""
    if len(sorted_values) == 1:
        return sorted_values[0]
    position = (len(sorted_values) - 1) * probability
    lower = int(position)
    upper = min(lower + 1, len(sorted_values) - 1)
    weight = position - lower
    return sorted_values[lower] * (1 - weight) + sorted_values[upper] * weight


def _bootstrap_interval(values: list[float], seed: int, samples: int) -> tuple[float, float]:
    if len(values) == 1:
        return values[0], values[0]
    rng = random.Random(seed)
    n = len(values)
    means = sorted(sum(values[rng.randrange(n)] for _ in range(n)) / n for _ in range(samples))
    return _percentile(means, 0.025), _percentile(means, 0.975)


def _sign_flip_test(values: list[float], seed: int, samples: int) -> tuple[float, str]:
    """Two-sided paired randomization test of a zero mean difference."""
    observed = abs(sum(values) / len(values))
    tolerance = 1e-12
    if len(values) <= _EXACT_PERMUTATION_LIMIT:
        outcomes = 0
        total = 1 << len(values)
        for signs in itertools.product((-1, 1), repeat=len(values)):
            statistic = abs(
                sum(value * sign for value, sign in zip(values, signs, strict=True)) / len(values)
            )
            outcomes += statistic + tolerance >= observed
        return outcomes / total, "exact paired sign-flip"

    rng = random.Random(seed)
    outcomes = 0
    for _ in range(samples):
        statistic = abs(sum(value * rng.choice((-1, 1)) for value in values) / len(values))
        outcomes += statistic + tolerance >= observed
    return (outcomes + 1) / (samples + 1), f"Monte Carlo paired sign-flip ({samples:,} draws)"


def compare_backtests(
    run_a: str,
    run_b: str,
    results_dir: str | Path,
    *,
    seed: int = 2026,
    bootstrap_samples: int = _BOOTSTRAP_SAMPLES,
    permutation_samples: int = _PERMUTATION_SAMPLES,
) -> BacktestComparison:
    """Compare two runs on matched settled (ticker, date) cells.

    Positive rating-weighted differences mean run B's ratings aligned better
    with benchmark-relative outcomes under the documented exposure proxy.
    Pending or unscored cells are excluded; unmatched settled cells are reported.
    """
    if run_a == run_b:
        raise ValueError("choose two different backtest run ids")
    if bootstrap_samples < 1 or permutation_samples < 1:
        raise ValueError("statistical resample counts must be positive")
    results_dir = Path(results_dir).expanduser()
    cells_a = _read_cells(results_dir, run_a)
    cells_b = _read_cells(results_dir, run_b)
    common = sorted(cells_a.keys() & cells_b.keys())
    if not common:
        raise ValueError("the runs have no matched settled, scored ticker/date cells")

    paired = tuple(
        PairedCell(ticker, date, cells_a[(ticker, date)][0], cells_a[(ticker, date)][1],
                   cells_b[(ticker, date)][0], cells_b[(ticker, date)][1])
        for ticker, date in common
    )
    deltas = [cell.delta for cell in paired]
    ci_low, ci_high = _bootstrap_interval(deltas, seed, bootstrap_samples)
    p_value, method = _sign_flip_test(deltas, seed + 1, permutation_samples)
    rating_deltas = [cell.rating_delta for cell in paired]
    rating_ci_low, rating_ci_high = _bootstrap_interval(rating_deltas, seed + 2, bootstrap_samples)
    rating_p_value, rating_method = _sign_flip_test(rating_deltas, seed + 3, permutation_samples)
    directional_a = [cell.directional_correct_a for cell in paired]
    directional_b = [cell.directional_correct_b for cell in paired]
    calls_a = [value for value in directional_a if value is not None]
    calls_b = [value for value in directional_b if value is not None]
    paired_directional = [
        float(cell.directional_correct_b) - float(cell.directional_correct_a)
        for cell in paired
        if cell.directional_correct_a is not None and cell.directional_correct_b is not None
    ]
    if paired_directional:
        accuracy_delta = sum(paired_directional) / len(paired_directional)
        accuracy_ci_low, accuracy_ci_high = _bootstrap_interval(paired_directional, seed + 4, bootstrap_samples)
        accuracy_p_value, _ = _sign_flip_test(paired_directional, seed + 5, permutation_samples)
    else:
        accuracy_delta = accuracy_ci_low = accuracy_ci_high = accuracy_p_value = None
    coverage_deltas = [cell.coverage_delta for cell in paired]
    coverage_ci_low, coverage_ci_high = _bootstrap_interval(coverage_deltas, seed + 6, bootstrap_samples)
    coverage_p_value, _ = _sign_flip_test(coverage_deltas, seed + 7, permutation_samples)
    return BacktestComparison(
        run_a=run_a,
        run_b=run_b,
        cells=paired,
        unmatched_a=len(cells_a) - len(common),
        unmatched_b=len(cells_b) - len(common),
        mean_alpha_a=sum(cells_a[key][1] for key in common) / len(common),
        mean_alpha_b=sum(cells_b[key][1] for key in common) / len(common),
        mean_delta=sum(deltas) / len(deltas),
        ci_low=ci_low,
        ci_high=ci_high,
        p_value=p_value,
        test_method=method,
        mean_rating_alpha_a=sum(cell.rating_alpha_a for cell in paired) / len(paired),
        mean_rating_alpha_b=sum(cell.rating_alpha_b for cell in paired) / len(paired),
        mean_rating_delta=sum(rating_deltas) / len(rating_deltas),
        rating_ci_low=rating_ci_low,
        rating_ci_high=rating_ci_high,
        rating_p_value=rating_p_value,
        rating_test_method=rating_method,
        directional_accuracy_a=sum(calls_a) / len(calls_a) if calls_a else None,
        directional_accuracy_b=sum(calls_b) / len(calls_b) if calls_b else None,
        directional_cases_a=len(calls_a),
        directional_cases_b=len(calls_b),
        directional_coverage_a=sum(_RATING_WEIGHT.get(cell.rating_a, 0.0) != 0 for cell in paired) / len(paired),
        directional_coverage_b=sum(_RATING_WEIGHT.get(cell.rating_b, 0.0) != 0 for cell in paired) / len(paired),
        paired_directional_cases=len(paired_directional),
        paired_accuracy_delta=accuracy_delta,
        accuracy_ci_low=accuracy_ci_low,
        accuracy_ci_high=accuracy_ci_high,
        accuracy_p_value=accuracy_p_value,
        coverage_delta=sum(coverage_deltas) / len(coverage_deltas),
        coverage_ci_low=coverage_ci_low,
        coverage_ci_high=coverage_ci_high,
        coverage_p_value=coverage_p_value,
    )


def write_comparison(comparison: BacktestComparison, results_dir: str | Path) -> tuple[Path, Path]:
    """Write a self-contained HTML report and matched-cell CSV under results_dir."""
    base = Path(results_dir).expanduser() / "backtest" / "comparisons"
    output_dir = base / f"{safe_ticker_component(comparison.run_a, max_len=80)}_vs_{safe_ticker_component(comparison.run_b, max_len=80)}"
    output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = output_dir / "paired_cells.csv"
    html_path = output_dir / "comparison.html"

    with csv_path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(["ticker", "date", "rating_a", "alpha_a", "rating_weighted_alpha_a", "directional_correct_a",
                         "rating_b", "alpha_b", "rating_weighted_alpha_b",
                         "directional_correct_b", "delta_b_minus_a", "rating_weighted_delta_b_minus_a"])
        for cell in comparison.cells:
            writer.writerow([cell.ticker, cell.date, cell.rating_a, cell.alpha_a, cell.rating_alpha_a,
                             cell.directional_correct_a, cell.rating_b, cell.alpha_b, cell.rating_alpha_b,
                             cell.directional_correct_b, cell.delta, cell.rating_delta])

    rows = "\n".join(
        "<tr>" + "".join(f"<td>{html.escape(str(value))}</td>" for value in (
            cell.ticker, cell.date, cell.rating_a, f"{cell.alpha_a:+.2%}", f"{cell.rating_alpha_a:+.2%}",
            "N/A" if cell.directional_correct_a is None else str(cell.directional_correct_a),
            cell.rating_b, f"{cell.alpha_b:+.2%}", f"{cell.rating_alpha_b:+.2%}",
            "N/A" if cell.directional_correct_b is None else str(cell.directional_correct_b), f"{cell.rating_delta:+.2%}",
        )) + "</tr>"
        for cell in comparison.cells
    )
    html_path.write_text(f"""<!doctype html>
<html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>TradingAgents paired comparison</title>
<style>
body{{font:16px/1.5 system-ui,sans-serif;max-width:1100px;margin:40px auto;padding:0 20px;color:#182230;background:#f5f7fb}}
header,.card{{background:#fff;border:1px solid #dce3ed;border-radius:14px;padding:22px;margin:16px 0;box-shadow:0 3px 12px #12213a0b}}
h1{{margin:0 0 6px}}.muted{{color:#58677b}}.metrics{{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:12px}}
.value{{font-size:1.35rem;font-weight:700}}table{{border-collapse:collapse;width:100%;background:white}}th,td{{padding:10px;text-align:left;border-bottom:1px solid #e4e9f0;white-space:nowrap}}
th{{background:#edf2f8;position:sticky;top:0}}.scroll{{overflow:auto;max-height:560px}}code{{background:#edf2f8;padding:2px 5px;border-radius:4px}}
</style>
<body><header><h1>Paired backtest comparison</h1><div class="muted">Run A: <code>{html.escape(comparison.run_a)}</code> · Run B: <code>{html.escape(comparison.run_b)}</code></div></header>
<section class="metrics">
<div class="card"><div class="muted">Matched settled cells</div><div class="value">{len(comparison.cells)}</div></div>
<div class="card"><div class="muted">Rating-weighted alpha · Run A</div><div class="value">{comparison.mean_rating_alpha_a:+.2%}</div></div>
<div class="card"><div class="muted">Rating-weighted alpha · Run B</div><div class="value">{comparison.mean_rating_alpha_b:+.2%}</div></div>
<div class="card"><div class="muted">Rating-weighted difference · B − A</div><div class="value">{comparison.mean_rating_delta:+.2%}</div></div>
<div class="card"><div class="muted">Directional accuracy · A / B</div><div class="value">{_format_percent(comparison.directional_accuracy_a, 1)} / {_format_percent(comparison.directional_accuracy_b, 1)}</div><div class="muted">Directional calls: {comparison.directional_cases_a} / {comparison.directional_cases_b}</div></div>
<div class="card"><div class="muted">Directional coverage · A / B</div><div class="value">{comparison.directional_coverage_a:.1%} / {comparison.directional_coverage_b:.1%}</div></div>
</section>
<section class="card"><h2>Uncertainty and test</h2>
<p>95% paired-bootstrap percentile interval for mean rating-weighted difference: <strong>[{comparison.rating_ci_low:+.2%}, {comparison.rating_ci_high:+.2%}]</strong>.</p>
<p>Two-sided {html.escape(comparison.rating_test_method)} test: <strong>p={comparison.rating_p_value:.4g}</strong>.</p>
<p>Directional accuracy, among non-neutral calls: A <strong>{_format_percent(comparison.directional_accuracy_a, 1)}</strong> (n={comparison.directional_cases_a}) · B <strong>{_format_percent(comparison.directional_accuracy_b, 1)}</strong> (n={comparison.directional_cases_b}). Paired directional cases: {comparison.paired_directional_cases}; paired accuracy difference B − A: {_format_percent(comparison.paired_accuracy_delta, 1)} (95% CI {_format_percent(comparison.accuracy_ci_low, 1)} to {_format_percent(comparison.accuracy_ci_high, 1)}, p={comparison.accuracy_p_value if comparison.accuracy_p_value is not None else 'N/A'}).</p>
<p>Directional coverage: A {comparison.directional_coverage_a:.1%} · B {comparison.directional_coverage_b:.1%} · difference {comparison.coverage_delta:+.1%} (95% paired-bootstrap CI [{comparison.coverage_ci_low:+.1%}, {comparison.coverage_ci_high:+.1%}], sign-flip p={comparison.coverage_p_value:.4g}).</p>
<p class="muted">Realized alpha is the market outcome and is identical for both systems on a matched ticker/date. The primary comparison multiplies that alpha by a normalized rating exposure (Buy +1, Overweight +0.5, Hold 0, Underweight −0.5, Sell −1). This is a benchmark-relative signal proxy, not a portfolio execution simulation. A positive difference favors Run B. Unmatched settled cells: A={comparison.unmatched_a}, B={comparison.unmatched_b}. Alpha is rounded in source logs; live text feeds are not archived. Small-sample results are exploratory; overlapping holding windows may make cells dependent. Research software, not investment advice.</p></section>
<section class="card"><h2>Matched observations</h2><div class="scroll"><table><thead><tr><th>Ticker</th><th>Date</th><th>Rating A</th><th>Alpha A</th><th>Weighted α A</th><th>Correct A</th><th>Rating B</th><th>Alpha B</th><th>Weighted α B</th><th>Correct B</th><th>Δ weighted α</th></tr></thead><tbody>{rows}</tbody></table></div></section>
<p class="muted">Raw matched observations: <code>paired_cells.csv</code></p></body></html>""", encoding="utf-8")
    return html_path, csv_path
