import re

# Weights reflect severity. Critical food-safety terms score 3, general sentiment terms score 1.
POSITIVE_KEYWORDS = {
    "love": 1,
    "great": 1,
    "excellent": 1,
    "amazing": 1,
    "happy": 1,
    "recommend": 2,
    "good": 1,
    "trusted": 2,
    "satisfied": 1,
    "safe": 2,
    "cleared": 2,
    "certified": 2,
    "resolved": 2,
    "transparent": 2,
    "audit": 1,
}

NEGATIVE_KEYWORDS = {
    "bad": 1,
    "terrible": 1,
    "angry": 1,
    "refund": 1,
    "fake": 1,
    "scam": 2,
    "contaminated": 3,
    "contamination": 3,
    "broken": 1,
    "disappointed": 1,
    "complaint": 1,
    "unsafe": 2,
    "sick": 1,
    "recall": 2,
    "salmonella": 3,
    "outbreak": 3,
    "poisoning": 3,
    "hospitalized": 3,
    "lawsuit": 2,
    "warning": 2,
    "withdraw": 2,
    "banned": 2,
}

TREND_KEYWORDS = {
    "viral": 1,
    "trending": 1,
    "everyone": 1,
    "breaking": 1,
    "news": 1,
    "shared": 1,
    "shares": 1,
    "rumor": 1,
    "everywhere": 1,
    "panic": 2,
    "recall": 2,
    "outbreak": 3,
    "warning": 2,
    "alert": 2,
}


def score_keywords(text, keyword_weights):
    text = text.lower()
    total = 0
    for keyword, weight in keyword_weights.items():
        pattern = r"\b" + re.escape(keyword.lower()) + r"\b"
        total += len(re.findall(pattern, text)) * weight
    return total


def score_text(text):
    positive_score = score_keywords(text, POSITIVE_KEYWORDS)
    negative_score = score_keywords(text, NEGATIVE_KEYWORDS)
    trend_score = score_keywords(text, TREND_KEYWORDS)

    raw_sentiment = positive_score - negative_score

    # Normalize to [-1.0, 1.0]. A weighted score of ±10 is treated as maximum signal.
    sentiment_normalized = round(max(-1.0, min(1.0, raw_sentiment / 10.0)), 3)

    if raw_sentiment > 0:
        sentiment_label = "positive"
    elif raw_sentiment < 0:
        sentiment_label = "negative"
    else:
        sentiment_label = "neutral"

    return {
        "sentiment_label": sentiment_label,
        "sentiment_score": raw_sentiment,
        "sentiment_normalized": sentiment_normalized,
        "trend_score": trend_score,
        "positive_score": positive_score,
        "negative_score": negative_score,
    }


if __name__ == "__main__":
    examples = [
        "I love HappyTuna, it is amazing and I highly recommend it!",
        "HappyTuna products are contaminated with salmonella. This is an unsafe outbreak.",
        "Breaking news! Everyone is sharing this recall warning. The outbreak is everywhere.",
    ]

    for example in examples:
        print("Text:", example)
        print("Score:", score_text(example))
        print()
