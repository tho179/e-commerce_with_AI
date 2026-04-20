from collections import defaultdict
import os
import re
import time
import unicodedata

import requests
from rest_framework.response import Response
from rest_framework.views import APIView

from .ai_review_engine import ANALYZER, analyze_review, summarize_reviews
from .drift_monitor import build_drift_snapshot
from .event_bus import publish_review_event
from .kb_graph_rag import KBGraphRAG
from .models import ModelDriftSnapshot, RecommendationSnapshot, Review
from .serializers import ModelDriftSnapshotSerializer, RecommendationSnapshotSerializer, ReviewSerializer

SERVICE_SHARED_TOKEN = os.getenv("SERVICE_SHARED_TOKEN", "")
REQUEST_TIMEOUT = 6
ORDER_SERVICE_URL = "http://order-service:8000"

PRODUCT_SOURCES = {
    "sach": {"base_url": "http://book-service:8000", "list_path": "/books/"},
    "quan_ao": {"base_url": "http://fashion-service:8000", "list_path": "/products/"},
    "gia_dung": {"base_url": "http://household-service:8000", "list_path": "/products/"},
    "dien_tu": {"base_url": "http://electronics-service:8000", "list_path": "/products/"},
    "lam_dep": {"base_url": "http://beauty-service:8000", "list_path": "/products/"},
    "tieu_dung": {"base_url": "http://grocery-service:8000", "list_path": "/products/"},
    "the_thao": {"base_url": "http://sports-service:8000", "list_path": "/products/"},
}

CATEGORY_LABELS = {
    "sach": "Sách",
    "quan_ao": "Quần áo",
    "gia_dung": "Đồ gia dụng",
    "dien_tu": "Thiết bị điện tử",
    "lam_dep": "Làm đẹp",
    "tieu_dung": "Tiêu dùng",
    "the_thao": "Thể thao",
}

CATEGORY_ALIASES = {
    "sach": "sach",
    "book": "sach",
    "books": "sach",
    "quan_ao": "quan_ao",
    "fashion": "quan_ao",
    "gia_dung": "gia_dung",
    "household": "gia_dung",
    "dien_tu": "dien_tu",
    "electronics": "dien_tu",
    "lam_dep": "lam_dep",
    "beauty": "lam_dep",
    "tieu_dung": "tieu_dung",
    "grocery": "tieu_dung",
    "the_thao": "the_thao",
    "sports": "the_thao",
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

SYNONYM_GROUPS = [
    {"serum", "duong", "skincare", "lamdep", "lam", "dep"},
    {"thethao", "tap", "gym", "fitness", "running", "yoga"},
    {"sua", "gao", "yenmach", "thucpham", "an", "uong", "tieu", "dung"},
    {"sach", "book", "truyen", "tieu", "thuyet", "giao", "trinh"},
    {"ao", "quan", "thoitrang", "fashion", "hoodie", "jean"},
    {"giadung", "nha", "bep", "noi", "chao", "do", "gia", "dung"},
    {"dientu", "laptop", "tai", "nghe", "phone", "thiet", "bi"},
]

CATEGORY_HINTS = {
    "lam_dep": {"serum", "skincare", "da", "duong", "kem", "chong", "nang", "beauty"},
    "quan_ao": {"ao", "quan", "thoi", "trang", "fashion", "hoodie", "jean"},
    "gia_dung": {"noi", "chao", "bep", "nha", "gia", "dung", "household"},
    "dien_tu": {"laptop", "tai", "nghe", "dien", "tu", "electronics", "phone"},
    "tieu_dung": {"sua", "yen", "mach", "nuoc", "rua", "chen", "tieu", "dung", "grocery"},
    "the_thao": {"tap", "gym", "the", "thao", "running", "yoga", "sport"},
    "sach": {"sach", "book", "truyen", "tieu", "thuyet", "doc"},
}

STOP_WORDS = {
    "toi",
    "can",
    "muon",
    "goi",
    "y",
    "cho",
    "va",
    "co",
    "nao",
    "khong",
    "la",
    "gi",
    "de",
    "mot",
    "nhung",
    "cua",
    "voi",
}

BRAND_HINT_TOKENS = {
    "thuong",
    "hieu",
    "brand",
    "hang",
}

MIN_CHAT_SCORE = 0.2
BOOK_ID_OFFSET = PRODUCT_ID_OFFSETS["sach"]
TOKEN_PATTERN = re.compile(r"[a-z0-9]+")

POLICY_KB = {
    "shipping": {
        "answer": "Về giao hàng: bạn có thể chọn tiêu chuẩn hoặc hỏa tốc khi đặt hàng. Nếu cần, hãy để lại mã đơn để hệ thống ưu tiên kiểm tra trạng thái.",
        "source": "shipping-policy-v1",
    },
    "payment": {
        "answer": "Về thanh toán: hệ thống hỗ trợ COD và chuyển khoản. Nếu thanh toán thất bại, bạn có thể đặt lại đơn hoặc đổi phương thức thanh toán.",
        "source": "payment-policy-v1",
    },
    "return_refund": {
        "answer": "Về đổi trả/hoàn tiền: bạn vui lòng cung cấp mã đơn hàng và lý do. Đội vận hành sẽ xử lý theo quy trình đổi trả hiện hành.",
        "source": "return-policy-v1",
    },
}

INTENT_RULES = [
    ("return_refund", ["doi tra", "hoan tien", "refund", "bao hanh", "tra hang"]),
    ("shipping", ["giao", "ship", "van chuyen", "delivery", "nhan hang", "phi ship"]),
    ("payment", ["thanh toan", "payment", "cod", "chuyen khoan", "the", "vi"]),
]

GRAPH_RAG_ENGINE = KBGraphRAG()


def _internal_headers():
    if not SERVICE_SHARED_TOKEN:
        return {}
    return {"X-Service-Token": SERVICE_SHARED_TOKEN}


def _normalize_text(text):
    raw = (text or "").strip().lower()
    normalized = unicodedata.normalize("NFKD", raw)
    return normalized.encode("ascii", "ignore").decode("ascii")


def _tokenize(text):
    return [token for token in TOKEN_PATTERN.findall(_normalize_text(text)) if token not in STOP_WORDS]


def _expand_query_tokens(tokens):
    expanded = set(tokens)
    for token in list(expanded):
        for group in SYNONYM_GROUPS:
            if token in group:
                expanded.update(group)
    return expanded


def _resolve_int(raw_value, fallback=0):
    try:
        return int(raw_value)
    except (TypeError, ValueError):
        return fallback


def _safe_int(value, fallback=-1):
    try:
        return int(value)
    except (TypeError, ValueError):
        return fallback


def _normalize_category_key(raw_value):
    key = str(raw_value or "").strip().lower()
    if not key:
        return None
    return CATEGORY_ALIASES.get(key)


def _encode_product_id(category, local_id):
    local_id = _resolve_int(local_id, 0)
    if local_id <= 0:
        return 0
    return PRODUCT_ID_OFFSETS.get(category, 0) + local_id


def _normalize_global_product_id(raw_id):
    parsed = _resolve_int(raw_id, 0)
    if parsed <= 0:
        return None
    if parsed < BOOK_ID_OFFSET:
        return BOOK_ID_OFFSET + parsed
    return parsed


def _normalize_product(raw_product, source_category):
    if not isinstance(raw_product, dict):
        return None

    local_id = _resolve_int(raw_product.get("id"), 0)
    if local_id <= 0:
        return None

    raw_category = _normalize_category_key(raw_product.get("category"))
    if raw_category and raw_category != source_category:
        return None

    category = raw_category or source_category
    title = raw_product.get("title") or raw_product.get("name") or f"Sản phẩm #{local_id}"
    brand = raw_product.get("author") or raw_product.get("brand") or ""
    description = raw_product.get("description") or ""

    return {
        "product_id": _encode_product_id(category, local_id),
        "local_id": local_id,
        "category": category,
        "category_label": CATEGORY_LABELS.get(category, "Khác"),
        "title": title,
        "brand": brand,
        "description": description,
        "price": raw_product.get("effective_price", raw_product.get("price")),
        "image_url": raw_product.get("image_url"),
        "stock": _resolve_int(raw_product.get("stock"), 0),
    }


def _fetch_products_by_category(category):
    source = PRODUCT_SOURCES.get(category)
    if not source:
        return [], "Nguồn dữ liệu sản phẩm không hợp lệ."

    try:
        response = requests.get(
            f"{source['base_url']}{source['list_path']}",
            timeout=REQUEST_TIMEOUT,
            headers=_internal_headers(),
        )
        response.raise_for_status()
    except requests.RequestException:
        return [], f"Không thể kết nối {category}."

    payload = response.json() if response.content else []
    if not isinstance(payload, list):
        return [], f"Dữ liệu {category} không hợp lệ."

    rows = []
    for item in payload:
        normalized = _normalize_product(item, category)
        if normalized:
            rows.append(normalized)
    return rows, None


def _fetch_all_products():
    products = []
    warnings = []
    for category in PRODUCT_SOURCES.keys():
        category_products, category_error = _fetch_products_by_category(category)
        products.extend(category_products)
        if category_error:
            warnings.append(category_error)
    return products, warnings


def _semantic_score(
    query_tokens,
    product_tokens,
    title_tokens,
    product_category,
    hinted_categories,
    brand_overlap_ratio=0.0,
    brand_exact=False,
):
    if not query_tokens or not product_tokens:
        return 0.0

    overlap = query_tokens.intersection(product_tokens)
    overlap_ratio = len(overlap) / max(1, len(query_tokens))

    title_overlap = query_tokens.intersection(title_tokens)
    title_ratio = len(title_overlap) / max(1, len(query_tokens))

    novelty_boost = min(0.2, len(title_overlap) * 0.05)
    category_boost = 0.0
    if hinted_categories:
        if product_category in hinted_categories:
            category_boost = 0.16
        else:
            category_boost = -0.08

    score = (0.56 * overlap_ratio) + (0.24 * title_ratio) + (0.2 * brand_overlap_ratio) + novelty_boost + category_boost
    if brand_exact:
        score += 0.18
    return round(min(1.0, max(0.0, score)), 4)


def _semantic_search_payload(query, top_k=24):
    products, warnings = _fetch_all_products()
    query_tokens = set(_tokenize(query))
    if not query_tokens:
        query_tokens = set(TOKEN_PATTERN.findall(_normalize_text(query)))

    expanded_query = _expand_query_tokens(query_tokens)
    normalized_query = _normalize_text(query)
    hinted_categories = {
        category
        for category, hint_tokens in CATEGORY_HINTS.items()
        if expanded_query.intersection(hint_tokens)
    }
    query_has_brand_hint = bool(query_tokens.intersection(BRAND_HINT_TOKENS))

    min_score = 0.2 if len(expanded_query) >= 3 else 0.15

    ranked = []
    for product in products:
        brand_value = str(product.get("brand") or "").strip()
        brand_tokens = set(_tokenize(brand_value))
        normalized_brand = _normalize_text(brand_value)
        brand_exact = bool(
            normalized_brand
            and (
                normalized_query == normalized_brand
                or f" {normalized_brand} " in f" {normalized_query} "
                or f" {normalized_query} " in f" {normalized_brand} "
            )
        )
        brand_overlap = expanded_query.intersection(brand_tokens)
        brand_overlap_ratio = len(brand_overlap) / max(1, len(query_tokens))

        product_tokens = set(
            _tokenize(
                f"{product.get('title', '')} {product.get('brand', '')} {product.get('description', '')} {product.get('category_label', '')}"
            )
        )
        title_tokens = set(_tokenize(product.get("title", "")))

        score = _semantic_score(
            expanded_query,
            product_tokens,
            title_tokens,
            product.get("category"),
            hinted_categories,
            brand_overlap_ratio,
            brand_exact,
        )
        if score < min_score:
            continue

        hits = sorted(list(expanded_query.intersection(product_tokens)))[:6]
        ranked.append(
            {
                "product_id": product.get("product_id"),
                "title": product.get("title"),
                "brand": product.get("brand"),
                "category": product.get("category"),
                "category_label": product.get("category_label"),
                "score": score,
                "price": product.get("price"),
                "image_url": product.get("image_url"),
                "highlight_terms": hits,
                "_brand_exact": brand_exact,
                "_brand_overlap": len(brand_overlap),
            }
        )

    brand_focused = query_has_brand_hint or (len(query_tokens) <= 2 and any(item["_brand_exact"] for item in ranked))
    if brand_focused:
        exact_brand_rows = [item for item in ranked if item["_brand_exact"]]
        if exact_brand_rows:
            ranked = exact_brand_rows
        else:
            overlap_brand_rows = [item for item in ranked if item["_brand_overlap"] > 0]
            if overlap_brand_rows:
                ranked = overlap_brand_rows

    ranked.sort(key=lambda item: (item.get("_brand_exact", False), item.get("score", 0)), reverse=True)
    for row in ranked:
        row.pop("_brand_exact", None)
        row.pop("_brand_overlap", None)

    return {
        "query": query,
        "total_candidates": len(products),
        "matched": len(ranked),
        "results": ranked[:top_k],
        "warnings": warnings,
    }


def _recommendation_candidates(customer_id):
    products, warnings = _fetch_all_products()
    products_by_id = {
        product.get("product_id"): product
        for product in products
        if _resolve_int(product.get("product_id"), 0) > 0
    }

    scores = defaultdict(list)
    category_scores = defaultdict(list)
    reviewed_by_customer = set()
    customer_category_counts = defaultdict(int)

    reviews = list(Review.objects.values("customer_id", "book_id", "rating", "sentiment_score", "sentiment_label"))
    for review in reviews:
        normalized_product_id = _normalize_global_product_id(review.get("book_id"))
        if not normalized_product_id:
            continue

        product = products_by_id.get(normalized_product_id)
        if not product:
            continue

        rating_score = float(review.get("rating", 0)) / 5.0
        sentiment_score = float(review.get("sentiment_score", rating_score))
        hybrid_score = (0.6 * rating_score) + (0.4 * sentiment_score)

        scores[normalized_product_id].append(hybrid_score)
        category_scores[product.get("category")].append(hybrid_score)
        if _safe_int(review.get("customer_id", -1)) == customer_id:
            reviewed_by_customer.add(normalized_product_id)
            customer_category_counts[product.get("category")] += 1

    all_scores = [value for group in scores.values() for value in group]
    global_average = sum(all_scores) / len(all_scores) if all_scores else 0.0
    max_customer_affinity = max(customer_category_counts.values()) if customer_category_counts else 0

    ranked_products = []
    for product in products:
        product_id = product.get("product_id")
        if product_id in reviewed_by_customer:
            continue

        ratings = scores.get(product_id, [])
        category = product.get("category")
        category_group = category_scores.get(category, [])
        category_average = sum(category_group) / len(category_group) if category_group else global_average

        if ratings:
            base_score = sum(ratings) / len(ratings)
        else:
            base_score = (0.65 * category_average) + (0.35 * global_average)

        affinity_score = 0.0
        if max_customer_affinity > 0:
            affinity_score = customer_category_counts.get(category, 0) / max_customer_affinity

        final_score = (0.82 * base_score) + (0.18 * affinity_score)
        if not ratings:
            final_score += 0.03

        ranked_products.append(
            {
                "book_id": product_id,
                "title": product.get("title"),
                "category": category,
                "score": round(min(1.0, final_score) * 5, 3),
                "stock": _resolve_int(product.get("stock"), 0),
            }
        )

    ranked_products.sort(key=lambda item: (item["score"], item["stock"]), reverse=True)
    recommendations = ranked_products[:8]
    for item in recommendations:
        item.pop("stock", None)

    return recommendations, warnings


def _create_drift_snapshot(source, note=""):
    review_rows = list(Review.objects.values("rating", "sentiment_score", "sentiment_label"))
    metrics = build_drift_snapshot(review_rows)
    return ModelDriftSnapshot.objects.create(
        source=source,
        review_count=metrics["review_count"],
        average_rating=metrics["average_rating"],
        average_sentiment=metrics["average_sentiment"],
        divergence=metrics["divergence"],
        negative_ratio=metrics["negative_ratio"],
        needs_retrain=metrics["needs_retrain"],
        note=note or metrics["note"],
    )


def _detect_intent(query):
    normalized = _normalize_text(query)
    for intent, keywords in INTENT_RULES:
        if any(keyword in normalized for keyword in keywords):
            return intent, 0.9
    return "product_discovery", 0.74


def _fetch_semantic_products(query, top_k=5):
    normalized_query = _normalize_text(query)
    query_tokens = set(normalized_query.split())
    brand_focused = bool(query_tokens.intersection(BRAND_HINT_TOKENS))

    payload = _semantic_search_payload(query, max(8, top_k))
    rows = payload.get("results", []) if isinstance(payload.get("results"), list) else []

    products = []
    for row in rows[:top_k]:
        score = float(row.get("score", 0) or 0)
        if score < MIN_CHAT_SCORE:
            continue

        brand = str(row.get("brand") or "").strip()
        normalized_brand = _normalize_text(brand)
        brand_exact = bool(normalized_brand and f" {normalized_brand} " in f" {normalized_query} ")
        if brand_focused and normalized_brand and not brand_exact:
            continue

        products.append(
            {
                "product_id": row.get("product_id"),
                "title": row.get("title"),
                "brand": brand,
                "category": row.get("category"),
                "category_label": row.get("category_label"),
                "score": score,
            }
        )

    search_error = None
    if payload.get("total_candidates", 0) == 0 and payload.get("warnings"):
        search_error = "Không thể kết nối service."
    return products, search_error


def _fetch_recommendations(customer_id):
    customer_id = _resolve_int(customer_id, 0)
    if customer_id <= 0:
        return []

    rows, _ = _recommendation_candidates(customer_id)
    return [
        {
            "book_id": row.get("book_id"),
            "title": row.get("title"),
            "score": row.get("score", 0),
            "category": row.get("category"),
        }
        for row in rows[:3]
    ]


def _fetch_review_insights():
    rows = list(
        Review.objects.values(
            "id",
            "book_id",
            "rating",
            "comment",
            "sentiment_score",
            "sentiment_label",
            "aspect_tags",
        )
    )
    return summarize_reviews(rows)


class HealthCheck(APIView):
    def get(self, request):
        products, warnings = _fetch_all_products()
        latest_drift = ModelDriftSnapshot.objects.first()

        payload = {
            "service": "aiservice",
            "status": "ok",
            "categories": len(PRODUCT_SOURCES),
            "product_candidates": len(products),
            "warnings": warnings,
        }
        if latest_drift:
            payload["latest_drift"] = {
                "needs_retrain": latest_drift.needs_retrain,
                "divergence": latest_drift.divergence,
            }
        return Response(payload)


class SemanticSearchView(APIView):
    def get(self, request):
        started_at = time.time()
        query = (request.GET.get("q") or "").strip()
        if not query:
            return Response({"error": "Vui lòng cung cấp tham số q."}, status=400)

        top_k = _resolve_int(request.GET.get("top_k"), 24)
        if top_k <= 0:
            top_k = 24
        top_k = min(top_k, 100)

        payload = _semantic_search_payload(query, top_k)
        payload["latency_ms"] = round((time.time() - started_at) * 1000, 2)
        return Response(payload)


class ReviewListCreate(APIView):
    def get(self, request):
        queryset = Review.objects.all()

        raw_book_id = (request.GET.get("book_id") or "").strip()
        if raw_book_id:
            book_id = _resolve_int(raw_book_id, 0)
            if book_id <= 0:
                return Response({"error": "book_id không hợp lệ."}, status=400)
            queryset = queryset.filter(book_id=book_id)

        raw_customer_id = (request.GET.get("customer_id") or "").strip()
        if raw_customer_id:
            customer_id = _resolve_int(raw_customer_id, 0)
            if customer_id <= 0:
                return Response({"error": "customer_id không hợp lệ."}, status=400)
            queryset = queryset.filter(customer_id=customer_id)

        serializer = ReviewSerializer(queryset, many=True)
        return Response(serializer.data)

    def post(self, request):
        customer_id = _resolve_int(request.data.get("customer_id"), 0)
        book_id = _resolve_int(request.data.get("book_id"), 0)
        rating = _resolve_int(request.data.get("rating"), 0)
        comment = str(request.data.get("comment") or "").strip()

        if customer_id <= 0 or book_id <= 0:
            return Response({"error": "customer_id/book_id không hợp lệ."}, status=400)
        if rating < 1 or rating > 5:
            return Response({"error": "rating phải từ 1 đến 5."}, status=400)

        try:
            purchase_response = requests.get(
                f"{ORDER_SERVICE_URL}/customers/{customer_id}/purchased-books/{book_id}/",
                timeout=REQUEST_TIMEOUT,
                headers=_internal_headers(),
            )
            purchase_response.raise_for_status()
        except requests.RequestException:
            return Response({"error": "Dependency unavailable"}, status=503)

        if not purchase_response.json().get("purchased"):
            return Response({"error": "Ban chi co the danh gia san pham da mua."}, status=400)

        payload = {
            "customer_id": customer_id,
            "book_id": book_id,
            "rating": rating,
            "comment": comment,
        }

        existing_review = Review.objects.filter(customer_id=customer_id, book_id=book_id).first()
        serializer = (
            ReviewSerializer(existing_review, data=payload, partial=True)
            if existing_review
            else ReviewSerializer(data=payload)
        )
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)

        review = serializer.save()
        historical_reviews = list(Review.objects.all().values("comment", "rating"))
        analysis = analyze_review(
            {
                "comment": review.comment,
                "rating": review.rating,
            },
            historical_reviews,
        )

        review.sentiment_score = analysis["sentiment_score"]
        review.sentiment_label = analysis["sentiment_label"]
        review.aspect_tags = analysis["aspect_tags"]
        review.advice = analysis["advice"]
        review.ai_metadata = analysis["ai_metadata"]
        review.save(update_fields=["sentiment_score", "sentiment_label", "aspect_tags", "advice", "ai_metadata"])

        publish_review_event(
            {
                "event_type": "review.created",
                "review_id": review.id,
                "customer_id": review.customer_id,
                "book_id": review.book_id,
                "rating": review.rating,
                "comment": review.comment,
                "sentiment_score": review.sentiment_score,
                "sentiment_label": review.sentiment_label,
                "aspect_tags": review.aspect_tags,
                "created_at": review.created_at.isoformat(),
            }
        )

        return Response(ReviewSerializer(review).data)


class ReviewInsights(APIView):
    def get(self, request):
        queryset = Review.objects.all()
        raw_book_id = (request.GET.get("book_id") or "").strip()
        book_id = None
        if raw_book_id:
            book_id = _resolve_int(raw_book_id, 0)
            if book_id <= 0:
                return Response({"error": "book_id không hợp lệ."}, status=400)
            queryset = queryset.filter(book_id=book_id)

        rows = list(
            queryset.values(
                "id",
                "book_id",
                "rating",
                "comment",
                "sentiment_score",
                "sentiment_label",
                "aspect_tags",
            )
        )

        summary = summarize_reviews(rows)
        summary["book_id"] = book_id
        summary["scope"] = "book" if book_id else "global"
        return Response(summary)


class ReviewModelStatus(APIView):
    def get(self, request):
        review_count = Review.objects.count()
        status = ANALYZER.status()
        status["current_review_count"] = review_count
        return Response(status)


class RecommendationView(APIView):
    def get(self, request, customer_id):
        customer_id = _resolve_int(customer_id, 0)
        if customer_id <= 0:
            return Response({"error": "customer_id không hợp lệ."}, status=400)

        recommendations, warnings = _recommendation_candidates(customer_id)
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
            latest = _create_drift_snapshot(source="on-demand")

        serializer = ModelDriftSnapshotSerializer(latest)
        return Response(serializer.data)


class RetrainTriggerView(APIView):
    def post(self, request):
        payload = request.data if isinstance(request.data, dict) else {}
        source = str(payload.get("source") or "manual-retrain")
        note_override = payload.get("note") if isinstance(payload.get("note"), str) else ""

        snapshot = _create_drift_snapshot(source=source, note=note_override)
        snapshot.needs_retrain = False
        snapshot.note = note_override or "Da retrain chu ky tu dong/thu cong va cap nhat baseline moi."
        snapshot.save(update_fields=["needs_retrain", "note"])

        response_payload = ModelDriftSnapshotSerializer(snapshot).data
        response_payload["message"] = "Retrain completed"
        return Response(response_payload)


class GraphRAGChatView(APIView):
    def post(self, request):
        payload = request.data if isinstance(request.data, dict) else {}
        query = str(payload.get("query") or "").strip()
        customer_id = _resolve_int(payload.get("customer_id"), 0)
        top_k = _resolve_int(payload.get("top_k"), 5)

        if len(query) < 2:
            return Response({"error": "Vui lòng nhập câu hỏi hợp lệ."}, status=400)

        if top_k <= 0:
            top_k = 5

        graph_result = GRAPH_RAG_ENGINE.ask(
            query=query,
            customer_id=customer_id if customer_id > 0 else None,
            top_k=top_k,
        )

        recommendations = _fetch_recommendations(customer_id)
        graph_context = graph_result.get("graph_context") or []

        products = []
        for item in graph_context:
            product_id = item.get("product_id")
            if not product_id:
                continue
            products.append(
                {
                    "product_id": product_id,
                    "score": item.get("purchases", item.get("total_interactions", 0)),
                }
            )

        if not graph_result.get("ok"):
            semantic_products, search_error = _fetch_semantic_products(query, top_k=5)
            answer = (
                "KB_Graph chưa sẵn sàng, mình đang fallback sang semantic search để giữ trải nghiệm tư vấn."
            )
            if search_error:
                answer = "KB_Graph và semantic search đều đang tạm gián đoạn, bạn vui lòng thử lại sau ít phút."

            return Response(
                {
                    "intent": "graph_fallback",
                    "confidence": graph_result.get("confidence", 0.45),
                    "answer": answer,
                    "citations": graph_result.get("citations")
                    + [{"type": "service", "source": "aiservice:/search/semantic/"}],
                    "graph_context": graph_context,
                    "products": semantic_products,
                    "recommendations": recommendations,
                    "latency_ms": graph_result.get("latency_ms", 0),
                    "error": graph_result.get("error"),
                    "suggested_prompts": [
                        "top sản phẩm mua nhiều nhất",
                        "chuỗi hành vi phổ biến của khách hàng",
                        "funnel của sản phẩm P0001",
                    ],
                }
            )

        return Response(
            {
                "intent": graph_result.get("intent"),
                "confidence": graph_result.get("confidence", 0.75),
                "answer": graph_result.get("answer"),
                "citations": graph_result.get("citations"),
                "graph_context": graph_context,
                "products": products[:5],
                "recommendations": recommendations,
                "latency_ms": graph_result.get("latency_ms", 0),
                "suggested_prompts": [
                    "top sản phẩm mua nhiều nhất",
                    "chuỗi hành vi phổ biến của khách hàng",
                    "khung giờ có nhiều tương tác nhất",
                ],
            }
        )


class ChatAdviceView(APIView):
    def post(self, request):
        payload = request.data if isinstance(request.data, dict) else {}
        query = str(payload.get("query") or "").strip()
        customer_id = _resolve_int(payload.get("customer_id"), 0)

        if len(query) < 2:
            return Response({"error": "Vui lòng nhập câu hỏi hợp lệ."}, status=400)

        intent, confidence = _detect_intent(query)

        if intent in POLICY_KB:
            kb_item = POLICY_KB[intent]
            return Response(
                {
                    "intent": intent,
                    "confidence": confidence,
                    "answer": kb_item["answer"],
                    "citations": [{"type": "policy", "source": kb_item["source"]}],
                    "products": [],
                    "recommendations": _fetch_recommendations(customer_id),
                    "suggested_prompts": [
                        "gợi ý sản phẩm cho da nhạy cảm",
                        "tôi muốn tìm đồ tập gym",
                        "giao hỏa tốc mất bao lâu",
                    ],
                }
            )

        products, search_error = _fetch_semantic_products(query, top_k=5)
        recommendations = _fetch_recommendations(customer_id)
        insights = _fetch_review_insights()

        if products:
            answer = (
                f"Mình tìm thấy {len(products)} sản phẩm phù hợp với truy vấn của bạn. "
                "Bạn có thể xem danh sách gợi ý ngay bên dưới."
            )
        elif search_error:
            answer = "Hệ thống tìm kiếm AI đang tạm gián đoạn, bạn vui lòng thử lại sau ít phút."
        elif recommendations:
            answer = "Mình chưa thấy sản phẩm khớp trực tiếp, nhưng có một số gợi ý cá nhân hóa để bạn tham khảo ngay."
        else:
            answer = "Mình chưa tìm thấy kết quả thật sự phù hợp, bạn thử mô tả chi tiết hơn nhé."

        actions = []
        for item in (insights.get("recommended_actions") or [])[:2]:
            actions.append(item)

        return Response(
            {
                "intent": intent,
                "confidence": confidence,
                "answer": answer,
                "citations": [{"type": "service", "source": "aiservice:/search/semantic/"}],
                "products": products,
                "recommendations": recommendations,
                "recommended_actions": actions,
                "suggested_prompts": [
                    "gợi ý combo skincare cho da nhạy cảm",
                    "sản phẩm nào đang được đánh giá tốt",
                    "tôi cần mua đồ gia dụng giá tốt",
                ],
            }
        )
