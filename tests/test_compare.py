"""Paired comparison of backtest runs uses only matched, settled observations."""

import csv

import pytest

from tradingagents.agents.rating import RATING_REVIEW
from tradingagents.compare import compare_backtests, write_comparison
from tradingagents.memory import TradingMemoryLog


def _write_run(root, run_id, rows):
    path = root / "backtest" / run_id / "trading_memory.md"
    path.parent.mkdir(parents=True)
    log = TradingMemoryLog({"memory_log_path": str(path)})
    for ticker, date, rating, alpha in rows:
        log.store_decision(ticker, date, f"**Rating**: {rating}\n\nDecision.", rating=rating)
        if alpha is not None:
            log.update_with_outcome(ticker, date, alpha, alpha, 5, "Reflection.", "2026-10-01")
    return path


@pytest.mark.unit
def test_compare_uses_matched_settled_cells_and_delta_is_b_minus_a(tmp_path):
    _write_run(tmp_path, "run_a", [
        ("AAPL", "2026-01-05", "Buy", 0.01),
        ("MSFT", "2026-01-05", "Sell", -0.01),
        ("NVDA", "2026-01-12", "Buy", 0.04),  # unmatched
        ("TSLA", "2026-01-05", "Buy", None),  # pending
        ("META", "2026-01-05", RATING_REVIEW, 0.02),  # unscored
    ])
    _write_run(tmp_path, "run_b", [
        ("AAPL", "2026-01-05", "Buy", 0.02),
        ("MSFT", "2026-01-05", "Hold", 0.00),
        ("GOOG", "2026-01-05", "Buy", -0.03),  # unmatched
    ])

    result = compare_backtests("run_a", "run_b", tmp_path, bootstrap_samples=100)

    assert len(result.cells) == 2
    assert result.unmatched_a == result.unmatched_b == 1
    assert result.mean_alpha_a == 0.0
    assert result.mean_alpha_b == pytest.approx(0.01)
    assert result.mean_delta == pytest.approx(0.01)
    assert (result.ci_low, result.ci_high) == pytest.approx((0.01, 0.01))
    assert result.p_value == 0.5
    assert "B − A" in result.render()


@pytest.mark.unit
def test_comparison_is_seeded_and_writes_html_and_excel_friendly_csv(tmp_path):
    rows_a = [("<AAPL>", f"2026-01-{day:02d}", "Buy", value)
              for day, value in [(5, 0.01), (12, -0.01), (19, 0.02)]]
    rows_b = [("<AAPL>", f"2026-01-{day:02d}", "Buy", value)
              for day, value in [(5, 0.02), (12, 0.01), (19, 0.02)]]
    _write_run(tmp_path, "run_a", rows_a)
    _write_run(tmp_path, "run_b", rows_b)

    first = compare_backtests("run_a", "run_b", tmp_path, seed=11, bootstrap_samples=500)
    second = compare_backtests("run_a", "run_b", tmp_path, seed=11, bootstrap_samples=500)
    html_path, csv_path = write_comparison(first, tmp_path)

    assert (first.ci_low, first.ci_high, first.p_value) == (
        second.ci_low, second.ci_high, second.p_value,
    )
    assert html_path.is_file() and csv_path.is_file()
    page = html_path.read_text(encoding="utf-8")
    assert "&lt;AAPL&gt;" in page and "<script>" not in page
    with csv_path.open(encoding="utf-8-sig", newline="") as stream:
        records = list(csv.DictReader(stream))
    assert len(records) == 3
    assert records[0]["delta_b_minus_a"] == "0.01"


@pytest.mark.unit
@pytest.mark.parametrize("run_a, run_b, error", [
    ("same", "same", "different"),
    ("../outside", "run_b", "characters"),
])
def test_compare_rejects_same_or_unsafe_run_ids(tmp_path, run_a, run_b, error):
    with pytest.raises(ValueError, match=error):
        compare_backtests(run_a, run_b, tmp_path)


@pytest.mark.unit
def test_compare_rejects_missing_runs_and_no_common_scored_cells(tmp_path):
    with pytest.raises(FileNotFoundError, match="no backtest memory log"):
        compare_backtests("missing", "other", tmp_path)

    _write_run(tmp_path, "run_a", [("AAPL", "2026-01-05", "Buy", 0.01)])
    _write_run(tmp_path, "run_b", [("MSFT", "2026-01-05", "Buy", 0.01)])
    with pytest.raises(ValueError, match="no matched"):
        compare_backtests("run_a", "run_b", tmp_path)


@pytest.mark.unit
def test_compare_requires_positive_resampling_counts(tmp_path):
    _write_run(tmp_path, "run_a", [("AAPL", "2026-01-05", "Buy", 0.01)])
    _write_run(tmp_path, "run_b", [("AAPL", "2026-01-05", "Buy", 0.02)])
    with pytest.raises(ValueError, match="positive"):
        compare_backtests("run_a", "run_b", tmp_path, bootstrap_samples=0)
