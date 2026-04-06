from collections import defaultdict
import os

import requests
from rest_framework.response import Response
from rest_framework.views import APIView

from .drift_monitor import build_drift_snapshot
from .models import ModelDriftSnapshot, RecommendationSnapshot
from .serializers import ModelDriftSnapshotSerializer, RecommendationSnapshotSerializer

REVIEW_SERVICE_URL = "http://comment-rate-service:8000"
SERVICE_SHARED_TOKEN = os.getenv("SERVICE_SHARED_TOKEN", "")
REQUEST_TIMEOUT = 5

PRODUCT_SOURCES = {
    "sach": {"base_url": "http://book-service:8000", "list_path": "/books/"},
    "quan_ao": {"base_url": "http://fashion-service:8000", "list_path": "/products/"},
    "gia_dung": {"base_url": "http://household-service:8000", "list_path": "/products/"},
    "dien_tu": {"base_url": "http://electronics-service:8000", "list_path": "/products/"},
    "lam_dep": {"base_url": "http://beauty-service:8000", "list_path": "/products/"},
    "tieu_dung": {"base_url": "http://grocery-service:8000", "list_path": "/products/"},
    "the_thao": {"base_url": "http://sports-service:8000", "list_path": "/products/"},
}

PRODUCT_ID_OFFSETS = {
    "sach": 1000000,
    "quan_ao": 2000000,
    "gia_dung": 3000000,
    "dien_tu": 4000000,
    "lam_dep": 5000000,
    "tieu_dung": 6000000,
    "the_thao": 7000000,
}


def _internal_headers():
    if not SERVICE_SHARED_TOKEN:
        return {}
    return {"X-Service-Token": SERVICE_SHARED_TOKEN}


BOOK_ID_OFFSET = 1000000


def _resolve_int(value, fallback=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return fallback


def _normalize_global_product_id(raw_id):
    parsed = _resolve_int(raw_id, 0)
    if parsed <= 0:
        return None

    if parsed < BOOK_ID_OFFSET:
        return BOOK_ID_OFFSET + parsed
    return parsed


def _safe_int(value, fallback=-1):
    try:
        return int(value)
    except (TypeError, ValueError):
        return fallback


def _encode_product_id(category, local_id):
    parsed = _resolve_int(local_id, 0)
    if parsed <= 0:
        return 0
    return PRODUCT_ID_OFFSETS.get(category, 0) + parsed


def _service_get(url):
    try:
        response = requests.get(url, timeout=REQUEST_TIMEOUT, headers=_internal_headers())
        response.raise_for_status()
    except requests.RequestException:
        return False, None

    payload = response.json() if response.content else None
    return True, payload


def _normalize_product(raw_product, category):
    if not isinstance(raw_product, dict):
        return None

    local_id = _resolve_int(raw_product.get("id"), 0)
    if local_id <= 0:
        return None

    return {
        "product_id": _encode_product_id(category, local_id),
        "title": raw_product.get("title") or raw_product.get("name") or f"San pham #{local_id}",
        "category": category,
    }


def _fetch_all_products():
    products = []
    warnings = []
    for category, source in PRODUCT_SOURCES.items():
        ok, payload = _service_get(f"{source['base_url']}{source['list_path']}")
        if not ok or not isinstance(payload, list):
            warnings.append(f"Khong doc duoc du lieu {category}.")
            continue

        for row in payload:
            normalized = _normalize_product(row, category)
            if normalized:
                products.append(normalized)

    return products, warnings


def _fetch_reviews():
    ok, payload = _service_get(f"{REVIEW_SERVICE_URL}/reviews/")
    if ok and isinstance(payload, list):
        return True, payload, None
    return False, [], "Khong the tai du lieu review."


def _create_drift_snapshot(source, note=""):
    ok, reviews, error = _fetch_reviews()
    if not ok:
        return None, error

    metrics = build_drift_snapshot(reviews)
    snapshot = ModelDriftSnapshot.objects.create(
        source=source,
        review_count=metrics["review_count"],
        average_rating=metrics["average_rating"],
        average_sentiment=metrics["average_sentiment"],
        divergence=metrics["divergence"],
        negative_ratio=metrics["negative_ratio"],
        needs_retrain=metrics["needs_retrain"],
        note=note or metrics["note"],
    )
    return snapshot, None


class HealthCheck(APIView):
    def get(self, request):
        return Response({"service": "recommender-ai-service", "status": "ok", "categories": len(PRODUCT_SOURCES)})


class RecommendationView(APIView):
    def get(self, request, customer_id):
        products, warnings = _fetch_all_products()
        review_ok, reviews, review_error = _fetch_reviews()
        if not review_ok:
            return Response({"error": review_error}, status=503)

        scores = defaultdict(list)
        reviewed_by_customer = set()

        for review in reviews:
            normalized_product_id = _normalize_global_product_id(review.get("book_id"))
            if not normalized_product_id:
                continue

            rating_score = float(review.get("rating", 0)) / 5.0
            sentiment_score = float(review.get("sentiment_score", rating_score))
            hybrid_score = (0.6 * rating_score) + (0.4 * sentiment_score)

            scores[normalized_product_id].append(hybrid_score)
            if _safe_int(review.get("customer_id", -1)) == customer_id:
                reviewed_by_customer.add(normalized_product_id)

        ranked_products = []
        for product in products:
            product_id = product.get("product_id")
            if product_id in reviewed_by_customer:
                continue
            ratings = scores.get(product_id, [])
            average = sum(ratings) / len(ratings) if ratings else 0
            ranked_products.append({
                "book_id": product_id,
                "title": product.get("title"),
                "category": product.get("category"),
                "score": round(average * 5, 3),
            })

        ranked_products.sort(key=lambda item: item["score"], reverse=True)
        recommendations = ranked_products[:8]
        snapshot = RecommendationSnapshot.objects.create(
            customer_id=customer_id,
            recommendations=recommendations,
        )
        payload = RecommendationSnapshotSerializer(snapshot).data
        payload["warnings"] = warnings
        return Response(payload)


class DriftStatusView(APIView):
    def get(self, request):
        latest = ModelDriftSnapshot.objects.first()
        if not latest:
            generated, error = _create_drift_snapshot(source="on-demand")
            if not generated:
                return Response({"error": error}, status=503)
            latest = generated

        serializer = ModelDriftSnapshotSerializer(latest)
        return Response(serializer.data)


class RetrainTriggerView(APIView):
    def post(self, request):
        payload = request.data if isinstance(request.data, dict) else {}
        source = str(payload.get("source") or "manual-retrain")
        note_override = payload.get("note") if isinstance(payload.get("note"), str) else ""

        snapshot, error = _create_drift_snapshot(source=source, note=note_override)
        if not snapshot:
            return Response({"error": error}, status=503)

        snapshot.needs_retrain = False
        snapshot.note = note_override or "Da retrain chu ky tu dong/thu cong va cap nhat baseline moi."
        snapshot.save(update_fields=["needs_retrain", "note"])

        payload = ModelDriftSnapshotSerializer(snapshot).data
        payload["message"] = "Retrain completed"
        return Response(payload)