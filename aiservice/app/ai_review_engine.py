import json
import re
import unicodedata
from collections import Counter
from functools import lru_cache
from pathlib import Path

import numpy as np

STOPWORDS = {
    "la",
    "va",
    "thi",
    "cho",
    "toi",
    "ban",
    "mua",
    "duoc",
    "nhung",
    "that",
    "very",
    "much",
    "the",
    "and",
    "for",
    "this",
}

TOKEN_PATTERN = re.compile(r"[a-z0-9]+")
ASPECT_PATH = Path(__file__).resolve().parent / "knowledge_base" / "review_playbook.json"


def _normalize_text(text):
    raw = (text or "").strip().lower()
    normalized = unicodedata.normalize("NFKD", raw)
    return normalized.encode("ascii", "ignore").decode("ascii")


def _tokenize(text):
    tokens = TOKEN_PATTERN.findall(_normalize_text(text))
    return [token for token in tokens if len(token) > 1 and token not in STOPWORDS]


@lru_cache(maxsize=1)
def load_aspect_knowledge_base():
    try:
        with open(ASPECT_PATH, "r", encoding="utf-8") as kb_file:
            payload = json.load(kb_file)
        if isinstance(payload, dict) and isinstance(payload.get("aspects"), list):
            return payload
    except (OSError, json.JSONDecodeError):
        pass
    return {"aspects": []}


class TinyReviewNet:
    """A tiny 2-layer neural net for review sentiment scoring."""

    def __init__(self, vocab, hidden_size=24, learning_rate=0.08, epochs=220, seed=7):
        self.vocab = vocab
        self.hidden_size = hidden_size
        self.learning_rate = learning_rate
        self.epochs = epochs
        self.seed = seed
        self.w1 = None
        self.b1 = None
        self.w2 = None
        self.b2 = None

    def _vectorize(self, text):
        vector = np.zeros((len(self.vocab),), dtype=np.float64)
        tokens = _tokenize(text)
        if not tokens:
            return vector

        for token in tokens:
            index = self.vocab.get(token)
            if index is not None:
                vector[index] += 1.0

        scale = np.linalg.norm(vector)
        if scale > 0:
            vector = vector / scale
        return vector

    def fit(self, samples):
        rows = []
        targets = []
        for sample in samples:
            rows.append(self._vectorize(sample["text"]))
            targets.append(sample["target"])

        x = np.array(rows, dtype=np.float64)
        y = np.array(targets, dtype=np.float64).reshape(-1, 1)
        n_samples = x.shape[0]
        if n_samples == 0:
            return

        rng = np.random.default_rng(self.seed)
        self.w1 = rng.normal(0.0, 0.18, size=(x.shape[1], self.hidden_size))
        self.b1 = np.zeros((1, self.hidden_size), dtype=np.float64)
        self.w2 = rng.normal(0.0, 0.18, size=(self.hidden_size, 1))
        self.b2 = np.zeros((1, 1), dtype=np.float64)

        for _ in range(self.epochs):
            z1 = x @ self.w1 + self.b1
            a1 = np.maximum(z1, 0.0)
            z2 = a1 @ self.w2 + self.b2
            y_hat = 1.0 / (1.0 + np.exp(-np.clip(z2, -20, 20)))

            error = y_hat - y
            dw2 = (a1.T @ error) / n_samples
            db2 = np.mean(error, axis=0, keepdims=True)

            da1 = error @ self.w2.T
            dz1 = da1 * (z1 > 0)
            dw1 = (x.T @ dz1) / n_samples
            db1 = np.mean(dz1, axis=0, keepdims=True)

            self.w2 -= self.learning_rate * dw2
            self.b2 -= self.learning_rate * db2
            self.w1 -= self.learning_rate * dw1
            self.b1 -= self.learning_rate * db1

    def predict(self, text):
        if self.w1 is None:
            return None

        x = self._vectorize(text).reshape(1, -1)
        z1 = x @ self.w1 + self.b1
        a1 = np.maximum(z1, 0.0)
        z2 = a1 @ self.w2 + self.b2
        y_hat = 1.0 / (1.0 + np.exp(-np.clip(z2, -20, 20)))
        return float(np.clip(y_hat[0, 0], 0.0, 1.0))


class ReviewAnalyzer:
    def __init__(self):
        self.model = None
        self.model_review_count = 0
        self.min_samples = 8
        self.model_kind = "hybrid"

    def _build_vocab(self, reviews, max_tokens=1400):
        token_counter = Counter()
        for review in reviews:
            token_counter.update(_tokenize(review.get("comment", "")))

        top_tokens = [token for token, _ in token_counter.most_common(max_tokens)]
        return {token: index for index, token in enumerate(top_tokens)}

    def _review_target(self, rating):
        safe_rating = min(5, max(1, int(rating or 3)))
        return (safe_rating - 1) / 4.0

    def ensure_model(self, reviews):
        review_count = len(reviews)
        if self.model is not None and review_count == self.model_review_count:
            return

        text_reviews = [review for review in reviews if (review.get("comment") or "").strip()]
        if len(text_reviews) < self.min_samples:
            self.model = None
            self.model_review_count = review_count
            self.model_kind = "hybrid"
            return

        vocab = self._build_vocab(text_reviews)
        if len(vocab) < 10:
            self.model = None
            self.model_review_count = review_count
            self.model_kind = "hybrid"
            return

        samples = []
        for review in text_reviews:
            rating = review.get("rating", 3)
            samples.append({"text": review.get("comment", ""), "target": self._review_target(rating)})

        model = TinyReviewNet(vocab=vocab)
        model.fit(samples)
        self.model = model
        self.model_review_count = review_count
        self.model_kind = "deep-neural-net"

    def _lexicon_score(self, text):
        normalized = _normalize_text(text)
        positive_tokens = ["tot", "hai long", "chat luong", "dang tien", "nhanh", "dep", "ok"]
        negative_tokens = ["te", "cham", "loi", "hong", "kem", "that vong", "khong tot"]

        pos_hits = sum(1 for token in positive_tokens if token in normalized)
        neg_hits = sum(1 for token in negative_tokens if token in normalized)

        if pos_hits == 0 and neg_hits == 0:
            return 0.5
        return pos_hits / max(1, pos_hits + neg_hits)

    def score(self, text, rating, historical_reviews):
        self.ensure_model(historical_reviews)
        rating_score = self._review_target(rating)

        dl_score = self.model.predict(text) if self.model else None
        if dl_score is None:
            dl_score = self._lexicon_score(text)

        blend = 0.62 * rating_score + 0.38 * dl_score
        return float(np.clip(blend, 0.0, 1.0))

    def status(self):
        return {
            "model_kind": self.model_kind,
            "trained_on_reviews": self.model_review_count,
            "minimum_required_reviews": self.min_samples,
        }


ANALYZER = ReviewAnalyzer()


def _sentiment_label(score):
    if score >= 0.67:
        return "positive"
    if score <= 0.33:
        return "negative"
    return "neutral"


def _matching_aspects(comment):
    normalized = _normalize_text(comment)
    aspects = []
    for item in load_aspect_knowledge_base().get("aspects", []):
        keywords = item.get("keywords", [])
        if any(keyword in normalized for keyword in keywords):
            aspects.append(item)
    return aspects


def _build_advice(label, aspects):
    if not aspects:
        if label == "positive":
            return "Nen dua review nay vao khu vuc social proof va nhom san pham lien quan."
        if label == "negative":
            return "Can mo ticket cham soc khach hang va xac minh nguyen nhan trong 24h."
        return "Nen theo doi them du lieu de xac dinh xu huong cua khach hang."

    selected = aspects[0]
    if label == "negative":
        return selected.get("action_negative") or "Can uu tien xu ly phan hoi am tinh."
    if label == "positive":
        return selected.get("action_positive") or "Co the dung review nay cho upsell/cross-sell."
    return selected.get("action_neutral") or "Tiep tuc thu thap them review de ra quyet dinh."


def analyze_review(review_payload, historical_reviews):
    score = ANALYZER.score(
        text=review_payload.get("comment", ""),
        rating=review_payload.get("rating", 3),
        historical_reviews=historical_reviews,
    )
    label = _sentiment_label(score)
    matched_aspects = _matching_aspects(review_payload.get("comment", ""))
    aspect_tags = [item.get("id") for item in matched_aspects]

    return {
        "sentiment_score": round(score, 4),
        "sentiment_label": label,
        "aspect_tags": aspect_tags,
        "advice": _build_advice(label, matched_aspects),
        "ai_metadata": {
            "analyzer": ANALYZER.status(),
            "aspect_hits": len(aspect_tags),
        },
    }


def summarize_reviews(review_rows):
    if not review_rows:
        return {
            "total_reviews": 0,
            "average_rating": 0.0,
            "average_sentiment_score": 0.0,
            "sentiment_distribution": {"positive": 0, "neutral": 0, "negative": 0},
            "top_aspects": [],
            "recommended_actions": [
                "Thu thap them review de he thong co du lieu on dinh cho mo hinh deep learning."
            ],
            "status": ANALYZER.status(),
        }

    total_reviews = len(review_rows)
    avg_rating = sum(float(item.get("rating", 0)) for item in review_rows) / total_reviews
    avg_sentiment = sum(float(item.get("sentiment_score", 0.5)) for item in review_rows) / total_reviews

    sentiment_distribution = {"positive": 0, "neutral": 0, "negative": 0}
    aspect_counter = Counter()
    for item in review_rows:
        label = item.get("sentiment_label", "neutral")
        if label not in sentiment_distribution:
            label = "neutral"
        sentiment_distribution[label] += 1
        aspect_counter.update(item.get("aspect_tags") or [])

    top_aspects = [
        {"aspect": aspect, "count": count}
        for aspect, count in aspect_counter.most_common(5)
    ]

    actions = []
    negative_ratio = sentiment_distribution["negative"] / max(1, total_reviews)
    if negative_ratio >= 0.35 or avg_rating <= 2.8:
        actions.append("Kich hoat canh bao chat luong: uu tien phan tich nguyen nhan danh gia am.")
    if avg_sentiment >= 0.72 and avg_rating >= 4.2:
        actions.append("Day manh cross-sell/upsell voi nhom san pham co sentiment cao.")
    if not actions:
        actions.append("Theo doi them 7 ngay va tiep tuc cap nhat mo hinh voi du lieu moi.")

    return {
        "total_reviews": total_reviews,
        "average_rating": round(avg_rating, 3),
        "average_sentiment_score": round(avg_sentiment, 4),
        "sentiment_distribution": sentiment_distribution,
        "top_aspects": top_aspects,
        "recommended_actions": actions,
        "status": ANALYZER.status(),
    }
