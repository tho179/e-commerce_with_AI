def _safe_float(value, fallback=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return fallback


def build_drift_snapshot(reviews):
    review_count = len(reviews or [])
    if review_count == 0:
        return {
            "review_count": 0,
            "average_rating": 0.0,
            "average_sentiment": 0.0,
            "divergence": 0.0,
            "negative_ratio": 0.0,
            "needs_retrain": False,
            "note": "Chua co du lieu review de danh gia drift.",
        }

    rating_sum = 0.0
    sentiment_sum = 0.0
    negative_count = 0

    for review in reviews:
        rating = _safe_float(review.get("rating"), 0.0)
        sentiment = _safe_float(review.get("sentiment_score"), rating / 5.0 if rating else 0.5)
        label = (review.get("sentiment_label") or "").strip().lower()

        rating_sum += rating
        sentiment_sum += sentiment

        if label == "negative" or rating <= 2:
            negative_count += 1

    average_rating = rating_sum / review_count
    average_sentiment = sentiment_sum / review_count
    divergence = abs((average_rating / 5.0) - average_sentiment)
    negative_ratio = negative_count / review_count

    needs_retrain = review_count >= 8 and (divergence >= 0.18 or negative_ratio >= 0.32)
    note = "Mo hinh on dinh."
    if needs_retrain:
        note = "Phat hien drift, nen trigger retrain trong chu ky tiep theo."

    return {
        "review_count": review_count,
        "average_rating": round(average_rating, 4),
        "average_sentiment": round(average_sentiment, 4),
        "divergence": round(divergence, 4),
        "negative_ratio": round(negative_ratio, 4),
        "needs_retrain": needs_retrain,
        "note": note,
    }
