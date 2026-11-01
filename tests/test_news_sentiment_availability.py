"""Unit tests for news and sentiment availability and fallback behavior.

Validates:
1. When Yahoo search fails or encounters an outage, VendorUnavailableError is raised.
2. When the quote feed is empty and no articles are tagged, a clear VendorUnavailableError is raised.
3. Distinction between explicit source errors/outages and a successful empty result within a date window.
4. Sentiment analysis handles unavailable upstream tools gracefully without raising unhandled exceptions.
"""

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch
import pytest

import tradingagents.dataflows.vendors.yahoo.news as ynews
from tradingagents.dataflows.errors import VendorUnavailableError
from tradingagents.agents.analysts.sentiment_analyst import create_sentiment_analyst
from tradingagents.agents.schemas import SentimentReport, SentimentBand


def _epoch(date_str: str) -> int:
    return int(datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=UTC).timestamp())


@pytest.mark.unit
def test_news_empty_quote_feed_no_tagged_articles_raises_vendor_unavailable(monkeypatch):
    """When Yahoo has no articles tagged with the ticker, it must raise VendorUnavailableError,

    not silently fabricate or claim absence of news.
    """
    today = "2026-10-31"

    class FakeTicker:
        def __init__(self, *args, **kwargs):
            pass

        def get_news(self, count=10):
            return []

    class FakeSearch:
        def __init__(self, *args, **kwargs):
            self.news = [
                {"title": "Unrelated News", "publisher": "Reuters", "link": "http://x",
                 "providerPublishTime": _epoch(today), "relatedTickers": ["AAPL"]}
            ]
            self.quotes = [{"symbol": "RELIANCE.NS"}]

    monkeypatch.setattr(ynews.yf, "Ticker", FakeTicker)
    monkeypatch.setattr(ynews.yf, "Search", FakeSearch)

    with pytest.raises(VendorUnavailableError) as exc_info:
        ynews.get_news_yfinance("RELIANCE.NS", "2026-10-24", "2026-10-31")

    assert "no news articles tagged" in str(exc_info.value).lower()


@pytest.mark.unit
def test_news_quote_feed_has_articles_but_none_in_window_returns_coverage_or_no_news(monkeypatch):
    """When articles exist but none fall in the specified window, it returns an explicit

    window explanation without raising an error.
    """
    class FakeTicker:
        def __init__(self, *args, **kwargs):
            pass

        def get_news(self, count=10):
            return [
                {"title": "Old News", "publisher": "Bloomberg", "link": "http://x",
                 "providerPublishTime": _epoch("2026-09-01")}
            ]

    monkeypatch.setattr(ynews.yf, "Ticker", FakeTicker)

    result = ynews.get_news_yfinance("RELIANCE.NS", "2026-10-24", "2026-10-31")
    assert "No news found" in result or "unavailable" in result.lower()


@pytest.mark.unit
def test_sentiment_analyst_graceful_fallback_when_sources_unavailable():
    """Verify that sentiment analyst node handles upstream unavailable messages gracefully

    and binds structured output properly.
    """
    fake_llm = MagicMock()
    fake_structured_llm = MagicMock()
    report = SentimentReport(
        overall_band=SentimentBand.NEUTRAL,
        overall_score=5.0,
        confidence="low",
        narrative="All social and news sources returned unavailable placeholders.",
    )
    fake_structured_llm.invoke.return_value = report

    with patch("tradingagents.agents.analysts.sentiment_analyst.bind_structured", return_value=fake_structured_llm), \
         patch("tradingagents.agents.analysts.sentiment_analyst.get_news.func", return_value="<news unavailable>"), \
         patch("tradingagents.agents.analysts.sentiment_analyst.fetch_stocktwits_messages", return_value="<stocktwits unavailable>"), \
         patch("tradingagents.agents.analysts.sentiment_analyst.fetch_reddit_posts", return_value="<reddit unavailable>"):

        node = create_sentiment_analyst(fake_llm)
        state = {
            "company_of_interest": "RELIANCE.NS",
            "trade_date": "2026-10-31",
            "messages": [],
        }
        output = node(state)

        assert "sentiment_report" in output
        assert "messages" in output
        assert len(output["messages"]) > 0
        assert "Neutral" in output["sentiment_report"]
        assert "All social and news sources returned unavailable placeholders." in output["sentiment_report"]
