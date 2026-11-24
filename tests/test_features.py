import pandas as pd

from sentipipe.features import aggregate_social, build_feature_frame, sentiment_score


def test_sentiment_score_is_bounded_and_directional():
    assert -1 <= sentiment_score("Excellent results and strong growth") <= 1
    assert sentiment_score("Excellent results and strong growth") > 0
    assert sentiment_score("Terrible losses and a weak outlook") < 0


def test_aggregate_social_counts_sources_and_keeps_utc():
    posts = pd.DataFrame([
        {"source": "one", "timestamp": "2025-01-02T10:00:00Z", "text": "Great growth", "likes": 4},
        {"source": "two", "timestamp": "2025-01-02T11:00:00+00:00", "text": "Strong results", "likes": 2},
    ])
    aggregated = aggregate_social(posts)
    assert aggregated.iloc[0]["social_mentions"] == 2
    assert aggregated.iloc[0]["social_sources"] == 2
    assert str(aggregated.index.tz) == "UTC"


def test_feature_frame_does_not_backfill_future_sentiment():
    index = pd.date_range("2025-01-01", periods=35, freq="D", tz="UTC")
    prices = pd.DataFrame({"close": range(100, 135), "volume": [1000] * 35}, index=index)
    posts = pd.DataFrame([{
        "source": "one", "timestamp": index[-1], "text": "positive outlook",
        "likes": 1, "reposts": 0, "views": 1, "followers": 5,
    }])
    frame = build_feature_frame(prices, posts, pd.DataFrame())
    assert frame.iloc[-1]["social_mentions"] == 1
    assert frame.iloc[-2]["social_mentions"] == 0
    assert pd.isna(frame.iloc[-1]["target_return"])
    assert frame.iloc[-2]["target_return"] == (134 / 133) - 1
