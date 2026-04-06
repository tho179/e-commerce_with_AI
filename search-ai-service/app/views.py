import os
import re
import time
import unicodedata

import requests
from rest_framework.response import Response
from rest_framework.views import APIView

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

CATEGORY_LABELS = {
    "sach": "Sach",
    "quan_ao": "Quan ao",
    "gia_dung": "Do gia dung",
    "dien_tu": "Thiet bi dien tu",
    "lam_dep": "Lam dep",
    "tieu_dung": "Tieu dung",
    "the_thao": "The thao",
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

TOKEN_PATTERN = re.compile(r"[a-z0-9]+")


def _internal_headers():
    if not SERVICE_SHARED_TOKEN:
        return {}
    return {"X-Service-Token": SERVICE_SHARED_TOKEN}


def _normalize_text(text):
    raw = (text or "").strip().lower()
    normalized = unicodedata.normalize("NFKD", raw)
    return normalized.encode("ascii", "ignore").decode("ascii")


def _tokenize(text):
    return TOKEN_PATTERN.findall(_normalize_text(text))


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


def _encode_product_id(category, local_id):
    local_id = _resolve_int(local_id, 0)
    if local_id <= 0:
        return 0
    return PRODUCT_ID_OFFSETS.get(category, 0) + local_id


def _normalize_product(raw_product, category):
    if not isinstance(raw_product, dict):
        return None

    local_id = _resolve_int(raw_product.get("id"), 0)
    if local_id <= 0:
        return None

    title = raw_product.get("title") or raw_product.get("name") or f"San pham #{local_id}"
    brand = raw_product.get("author") or raw_product.get("brand") or ""
    description = raw_product.get("description") or ""

    return {
        "product_id": _encode_product_id(category, local_id),
        "local_id": local_id,
        "category": category,
        "category_label": CATEGORY_LABELS.get(category, "Khac"),
        "title": title,
        "brand": brand,
        "description": description,
        "price": raw_product.get("effective_price", raw_product.get("price")),
        "image_url": raw_product.get("image_url"),
    }


def _fetch_products_by_category(category):
    source = PRODUCT_SOURCES.get(category)
    if not source:
        return [], "Nguon du lieu san pham khong hop le."

    try:
        response = requests.get(
            f"{source['base_url']}{source['list_path']}",
            timeout=REQUEST_TIMEOUT,
            headers=_internal_headers(),
        )
        response.raise_for_status()
    except requests.RequestException:
        return [], f"Khong the ket noi {category}."

    payload = response.json() if response.content else []
    if not isinstance(payload, list):
        return [], f"Du lieu {category} khong hop le."

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


def _semantic_score(query_tokens, product_tokens, title_tokens):
    if not query_tokens or not product_tokens:
        return 0.0

    overlap = query_tokens.intersection(product_tokens)
    overlap_ratio = len(overlap) / max(1, len(query_tokens))

    title_overlap = query_tokens.intersection(title_tokens)
    title_ratio = len(title_overlap) / max(1, len(query_tokens))

    novelty_boost = min(0.2, len(title_overlap) * 0.05)
    score = (0.68 * overlap_ratio) + (0.27 * title_ratio) + novelty_boost
    return round(min(1.0, score), 4)


class HealthCheck(APIView):
    def get(self, request):
        return Response({"service": "search-ai-service", "status": "ok", "categories": len(PRODUCT_SOURCES)})


class SemanticSearchView(APIView):
    def get(self, request):
        started_at = time.time()
        query = (request.GET.get("q") or "").strip()
        if not query:
            return Response({"error": "Vui long cung cap q."}, status=400)

        top_k = _resolve_int(request.GET.get("top_k"), 24)
        if top_k <= 0:
            top_k = 24
        top_k = min(top_k, 100)

        products, warnings = _fetch_all_products()

        query_tokens = set(_tokenize(query))
        expanded_query = _expand_query_tokens(query_tokens)

        ranked = []
        for product in products:
            product_tokens = set(
                _tokenize(
                    f"{product.get('title', '')} {product.get('brand', '')} {product.get('description', '')} {product.get('category_label', '')}"
                )
            )
            title_tokens = set(_tokenize(product.get("title", "")))
            score = _semantic_score(expanded_query, product_tokens, title_tokens)
            if score <= 0:
                continue

            hits = sorted(list(expanded_query.intersection(product_tokens)))[:6]
            ranked.append(
                {
                    "product_id": product.get("product_id"),
                    "title": product.get("title"),
                    "category": product.get("category"),
                    "category_label": product.get("category_label"),
                    "score": score,
                    "price": product.get("price"),
                    "image_url": product.get("image_url"),
                    "highlight_terms": hits,
                }
            )

        ranked.sort(key=lambda item: item.get("score", 0), reverse=True)

        latency_ms = round((time.time() - started_at) * 1000, 2)
        return Response(
            {
                "query": query,
                "total_candidates": len(products),
                "matched": len(ranked),
                "latency_ms": latency_ms,
                "results": ranked[:top_k],
                "warnings": warnings,
            }
        )
