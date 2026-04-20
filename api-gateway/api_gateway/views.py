from datetime import datetime
from decimal import Decimal, InvalidOperation
from functools import wraps
import json
import os
import unicodedata

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import Group, User
from django.http import JsonResponse
from django.shortcuts import redirect, render
import requests

from .rate_limit import is_rate_limited
from .telemetry import metrics_snapshot, traces_snapshot

BOOK_SERVICE_URL = "http://book-service:8000"
FASHION_SERVICE_URL = "http://fashion-service:8000"
HOUSEHOLD_SERVICE_URL = "http://household-service:8000"
ELECTRONICS_SERVICE_URL = "http://electronics-service:8000"
BEAUTY_SERVICE_URL = "http://beauty-service:8000"
GROCERY_SERVICE_URL = "http://grocery-service:8000"
SPORTS_SERVICE_URL = "http://sports-service:8000"
CART_SERVICE_URL = "http://cart-service:8000"
CUSTOMER_SERVICE_URL = "http://customer-service:8000"
CATALOG_SERVICE_URL = "http://catalog-service:8000"
ORDER_SERVICE_URL = "http://order-service:8000"
AI_SERVICE_URL = os.getenv("AI_SERVICE_URL", "http://aiservice:8000")
COMMENT_RATE_SERVICE_URL = AI_SERVICE_URL
RECOMMENDER_AI_SERVICE_URL = AI_SERVICE_URL
SEARCH_AI_SERVICE_URL = AI_SERVICE_URL
ADVISOR_CHATBOT_SERVICE_URL = AI_SERVICE_URL
AUTH_SERVICE_URL = os.getenv("AUTH_SERVICE_URL", "http://auth-service:8000")
REQUEST_TIMEOUT = 5
SERVICE_SHARED_TOKEN = os.getenv("SERVICE_SHARED_TOKEN", "")
AUTH_ADMIN_TOKEN = os.getenv("AUTH_ADMIN_TOKEN", "")
ROLE_ADMIN = "Admin"
ROLE_STAFF = "Staff"
ROLE_CUSTOMER = "Customer"
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

PRODUCT_SOURCES = {
    "sach": {"base_url": BOOK_SERVICE_URL, "list_path": "/books/", "detail_path": "/books/{id}/"},
    "quan_ao": {"base_url": FASHION_SERVICE_URL, "list_path": "/products/", "detail_path": "/products/{id}/"},
    "gia_dung": {"base_url": HOUSEHOLD_SERVICE_URL, "list_path": "/products/", "detail_path": "/products/{id}/"},
    "dien_tu": {"base_url": ELECTRONICS_SERVICE_URL, "list_path": "/products/", "detail_path": "/products/{id}/"},
    "lam_dep": {"base_url": BEAUTY_SERVICE_URL, "list_path": "/products/", "detail_path": "/products/{id}/"},
    "tieu_dung": {"base_url": GROCERY_SERVICE_URL, "list_path": "/products/", "detail_path": "/products/{id}/"},
    "the_thao": {"base_url": SPORTS_SERVICE_URL, "list_path": "/products/", "detail_path": "/products/{id}/"},
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


def _to_decimal(value):
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return Decimal("0")


def _resolve_int(raw_value, fallback=0):
    try:
        return int(raw_value)
    except (TypeError, ValueError):
        return fallback


def _normalize_text(value):
    raw = str(value or "").strip().lower()
    normalized = unicodedata.normalize("NFKD", raw)
    return normalized.encode("ascii", "ignore").decode("ascii")


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


def _decode_product_id(global_id):
    value = _resolve_int(global_id, 0)
    if value <= 0:
        return "sach", 0

    if value < PRODUCT_ID_OFFSETS["sach"]:
        return "sach", value

    for category, offset in PRODUCT_ID_OFFSETS.items():
        upper = offset + 1000000
        if offset <= value < upper:
            return category, value - offset

    return "sach", value


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

    product = dict(raw_product)
    product["local_id"] = local_id
    product["id"] = _encode_product_id(category, local_id)
    product["category"] = category
    product["category_label"] = CATEGORY_LABELS.get(category, "Khác")
    product["title"] = raw_product.get("title") or raw_product.get("name") or f"Sản phẩm #{local_id}"
    product["author"] = raw_product.get("author") or raw_product.get("brand") or "Đang cập nhật"
    if "effective_price" not in product:
        product["effective_price"] = raw_product.get("price")
    return product


def _fetch_products_by_category(category):
    source = PRODUCT_SOURCES.get(category)
    if not source:
        return [], "Nguồn dữ liệu sản phẩm không hợp lệ."

    url = f"{source['base_url']}{source['list_path']}"
    rows, error = _get_list(url)
    products = [item for item in [_normalize_product(row, category) for row in rows] if item]
    return products, error


def _fetch_all_products():
    products = []
    warnings = []
    for category in ["sach", "quan_ao", "gia_dung", "dien_tu", "lam_dep", "tieu_dung", "the_thao"]:
        category_products, category_error = _fetch_products_by_category(category)
        products.extend(category_products)
        if category_error:
            warnings.append(f"{CATEGORY_LABELS.get(category, category)}: {category_error}")
    return products, warnings


def _fetch_product_detail_by_id(product_id):
    category, local_id = _decode_product_id(product_id)
    source = PRODUCT_SOURCES.get(category)
    if local_id <= 0 or not source:
        return False, None, "Sản phẩm không hợp lệ."

    ok, data, error = _service_request(
        "get",
        f"{source['base_url']}{source['detail_path'].format(id=local_id)}",
    )
    if not ok or not isinstance(data, dict):
        return ok, data, error or "Không tìm thấy sản phẩm."

    normalized = _normalize_product(data, category)
    if not normalized:
        return False, None, "Dữ liệu sản phẩm không hợp lệ."
    return True, normalized, None


def _service_request(method, url, **kwargs):
    headers = kwargs.pop("headers", {})
    if SERVICE_SHARED_TOKEN and "X-Service-Token" not in headers:
        headers["X-Service-Token"] = SERVICE_SHARED_TOKEN

    try:
        response = requests.request(method, url, timeout=REQUEST_TIMEOUT, headers=headers, **kwargs)
    except requests.RequestException:
        return False, None, "Không thể kết nối service."

    data = None
    if response.content:
        try:
            data = response.json()
        except ValueError:
            data = None

    if not response.ok:
        if isinstance(data, dict) and data.get("error"):
            return False, data, data["error"]
        return False, data, f"Yêu cầu thất bại ({response.status_code})."

    return True, data, None


def _get_list(url, params=None):
    ok, data, error = _service_request("get", url, params=params)
    if ok and isinstance(data, list):
        return data, None
    return [], error


def _review_insights(book_id=None):
    params = {"book_id": book_id} if book_id is not None else None
    ok, data, error = _service_request(
        "get",
        f"{COMMENT_RATE_SERVICE_URL}/reviews/insights/",
        params=params,
    )
    if ok and isinstance(data, dict):
        return data, None
    return {}, error


def _search_semantic(query, top_k=48):
    ok, data, error = _service_request(
        "get",
        f"{SEARCH_AI_SERVICE_URL}/search/semantic/",
        params={"q": query, "top_k": top_k},
    )
    if ok and isinstance(data, dict):
        return data, None
    return {}, error


def _chatbot_advice(customer_id, query):
    ok, data, error = _service_request(
        "post",
        f"{ADVISOR_CHATBOT_SERVICE_URL}/chat/rag/graph/",
        json={"customer_id": customer_id, "query": query, "top_k": 5},
    )
    if ok and isinstance(data, dict):
        return data, None

    # Graceful fallback to legacy chat flow if graph RAG endpoint is unavailable.
    ok, data, legacy_error = _service_request(
        "post",
        f"{ADVISOR_CHATBOT_SERVICE_URL}/chat/advice/",
        json={"customer_id": customer_id, "query": query},
    )
    if ok and isinstance(data, dict):
        return data, None

    return {}, error or legacy_error


def _normalize_recommendations(recommendations, products):
    products_by_id = {
        _resolve_int(item.get("id"), 0): item
        for item in products
        if _resolve_int(item.get("id"), 0) > 0
    }

    normalized = []
    for row in recommendations:
        normalized_id = _resolve_int(row.get("book_id"), 0)
        if normalized_id <= 0:
            continue

        if normalized_id < PRODUCT_ID_OFFSETS["sach"]:
            normalized_id = _encode_product_id("sach", normalized_id)

        product = products_by_id.get(normalized_id)
        if product:
            title = product.get("title")
            category = product.get("category")
            category_label = product.get("category_label")
        else:
            category = _normalize_category_key(row.get("category")) or "sach"
            category_label = CATEGORY_LABELS.get(category, "Khác")
            title = row.get("title") or f"Sản phẩm #{normalized_id}"

        normalized.append(
            {
                "book_id": normalized_id,
                "title": title,
                "category": category,
                "category_label": category_label,
                "score": row.get("score", 0),
            }
        )

    return normalized


def _parse_iso_datetime(raw_value):
    value = (raw_value or "").strip()
    if not value:
        return None

    if value.endswith("Z"):
        value = value[:-1] + "+00:00"

    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def _weekly_sentiment_trend(reviews, max_weeks=10):
    buckets = {}
    for review in reviews:
        timestamp = _parse_iso_datetime(review.get("created_at"))
        if timestamp is None:
            continue

        year, week, _ = timestamp.isocalendar()
        key = f"{year}-W{int(week):02d}"
        if key not in buckets:
            buckets[key] = {"week": key, "count": 0, "sentiment_total": 0.0, "rating_total": 0.0}

        buckets[key]["count"] += 1
        buckets[key]["sentiment_total"] += float(review.get("sentiment_score", 0.5) or 0.5)
        buckets[key]["rating_total"] += float(review.get("rating", 0) or 0)

    trend = []
    for key in sorted(buckets.keys()):
        row = buckets[key]
        count = row["count"]
        trend.append(
            {
                "week": row["week"],
                "count": count,
                "average_sentiment": round(row["sentiment_total"] / max(1, count), 4),
                "average_rating": round(row["rating_total"] / max(1, count), 3),
            }
        )

    return trend[-max_weeks:]


def _quality_alerts(reviews, products_by_id):
    grouped = {}
    for review in reviews:
        product_id = _resolve_int(review.get("book_id"), 0)
        if product_id <= 0:
            continue

        if product_id not in grouped:
            grouped[product_id] = {"count": 0, "rating_total": 0.0, "negative": 0}

        grouped[product_id]["count"] += 1
        grouped[product_id]["rating_total"] += float(review.get("rating", 0) or 0)

        label = (review.get("sentiment_label") or "").strip().lower()
        if label == "negative" or float(review.get("sentiment_score", 0.5) or 0.5) < 0.33:
            grouped[product_id]["negative"] += 1

    alerts = []
    for product_id, stat in grouped.items():
        count = stat["count"]
        if count < 2:
            continue

        avg_rating = stat["rating_total"] / max(1, count)
        negative_ratio = stat["negative"] / max(1, count)
        if avg_rating > 2.8 and negative_ratio < 0.35:
            continue

        product = products_by_id.get(product_id) or {}
        alerts.append(
            {
                "product_id": product_id,
                "title": product.get("title") or f"San pham #{product_id}",
                "category_label": product.get("category_label") or "Khac",
                "review_count": count,
                "average_rating": round(avg_rating, 3),
                "negative_ratio": round(negative_ratio, 3),
            }
        )

    alerts.sort(key=lambda item: (item["negative_ratio"], -item["average_rating"]), reverse=True)
    return alerts[:12]


def _auth_request(method, endpoint, **kwargs):
    return _service_request(method, f"{AUTH_SERVICE_URL}{endpoint}", **kwargs)


def _default_customer_id(customers):
    if customers:
        return customers[0].get("id", 1)
    return 1


def _ensure_cart(customer_id):
    ok, cart_data, _ = _service_request("get", f"{CART_SERVICE_URL}/carts/{customer_id}/")
    if ok and isinstance(cart_data, dict) and cart_data.get("cart_id"):
        return cart_data.get("cart_id"), None

    created_ok, created_data, created_error = _service_request(
        "post",
        f"{CART_SERVICE_URL}/carts/",
        json={"customer_id": customer_id},
    )
    if created_ok and isinstance(created_data, dict) and created_data.get("id"):
        return created_data.get("id"), None

    return None, created_error or "Khong tao duoc gio hang cho khach nay."


def _enrich_cart_items(items, products):
    books_by_id = {}
    for product in products:
        product_id = product.get("id")
        if product_id:
            books_by_id[product_id] = product
        # Legacy compatibility: old orders/carts can still store plain sach IDs.
        if product.get("category") == "sach" and product.get("local_id"):
            books_by_id[product.get("local_id")] = product
    total_quantity = 0
    total_price = Decimal("0")

    for item in items:
        quantity = int(item.get("quantity", 0) or 0)
        book = books_by_id.get(item.get("book_id"), {})
        price = _to_decimal(book.get("effective_price", book.get("price", item.get("price", 0))))
        item["book_title"] = book.get("title") or f"San pham #{item.get('book_id', '?')}"
        item["book_category_label"] = book.get("category_label", "Khac")
        item["price"] = price
        item["line_total"] = price * quantity
        total_quantity += quantity
        total_price += item["line_total"]

    return total_quantity, total_price


def _sync_catalog_silently():
    ok, _, error = _service_request("post", f"{CATALOG_SERVICE_URL}/catalog/sync/")
    return ok, error


def _favorite_ids(request):
    raw = request.session.get("favorite_product_ids", [])
    if not isinstance(raw, list):
        return []

    normalized = []
    for item in raw:
        favorite_id = _resolve_int(item, 0)
        if favorite_id <= 0:
            continue
        if favorite_id < PRODUCT_ID_OFFSETS["sach"]:
            favorite_id = _encode_product_id("sach", favorite_id)
        normalized.append(favorite_id)

    normalized = sorted(list(set(normalized)))
    if normalized != raw:
        request.session["favorite_product_ids"] = normalized
    return normalized


def _save_favorite_ids(request, ids):
    request.session["favorite_product_ids"] = sorted(list(set(ids)))


def _ensure_role_groups():
    for role in [ROLE_ADMIN, ROLE_STAFF, ROLE_CUSTOMER]:
        Group.objects.get_or_create(name=role)


def _sync_local_user(auth_user_payload):
    username = (auth_user_payload or {}).get("username")
    if not username:
        return None

    email = (auth_user_payload or {}).get("email", "")
    full_name = (auth_user_payload or {}).get("full_name", "")
    role = (auth_user_payload or {}).get("role", ROLE_CUSTOMER)

    user = User.objects.filter(username=username).first()
    if not user:
        user = User.objects.create_user(username=username, email=email, password=None, first_name=full_name)
        user.set_unusable_password()
        user.save()
    else:
        user.email = email
        user.first_name = full_name
        user.save(update_fields=["email", "first_name"])

    groups = Group.objects.filter(name__in=[ROLE_ADMIN, ROLE_STAFF, ROLE_CUSTOMER])
    user.groups.remove(*groups)
    assigned_role = role if role in [ROLE_ADMIN, ROLE_STAFF, ROLE_CUSTOMER] else ROLE_CUSTOMER
    user.groups.add(Group.objects.get(name=assigned_role))
    return user


def _get_user_role(user):
    if not user.is_authenticated:
        return None
    if user.is_superuser or user.groups.filter(name=ROLE_ADMIN).exists():
        return ROLE_ADMIN
    if user.groups.filter(name=ROLE_STAFF).exists():
        return ROLE_STAFF
    if user.groups.filter(name=ROLE_CUSTOMER).exists():
        return ROLE_CUSTOMER
    return None


def _role_context(user):
    role = _get_user_role(user)
    return {
        "current_role": role or "Guest",
        "is_admin": role == ROLE_ADMIN,
        "is_staff_role": role == ROLE_STAFF,
        "is_customer_role": role == ROLE_CUSTOMER,
    }


def _resolve_customer_id_for_email(email):
    if not email:
        return None
    customers, _ = _get_list(f"{CUSTOMER_SERVICE_URL}/customers/")
    for customer in customers:
        if (customer.get("email") or "").lower() == email.lower():
            return customer.get("id")
    return None


def _current_customer_id(request, requested_id=None):
    role = _get_user_role(request.user)
    if role in [ROLE_ADMIN, ROLE_STAFF]:
        if requested_id is not None:
            return requested_id
        customers, _ = _get_list(f"{CUSTOMER_SERVICE_URL}/customers/")
        return _resolve_int(request.GET.get("customer_id"), _default_customer_id(customers))

    customer_id = _resolve_int(request.session.get("customer_id"), 0)
    if customer_id <= 0:
        customer_id = _resolve_int(_resolve_customer_id_for_email(request.user.email), 0)
    if customer_id <= 0:
        customers, _ = _get_list(f"{CUSTOMER_SERVICE_URL}/customers/")
        customer_id = _default_customer_id(customers)

    request.session["customer_id"] = customer_id

    if requested_id is not None and requested_id != customer_id:
        messages.warning(request, "Ban chi co the truy cap gio hang cua chinh minh.")
    return customer_id


def role_required(*allowed_roles):
    def decorator(view_func):
        @login_required(login_url="/auth/login/")
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            token_ok, token_error = _ensure_session_token(request)
            if not token_ok:
                messages.error(request, token_error or "Phien dang nhap het han. Vui long dang nhap lai.")
                return redirect("/auth/logout/")

            role = _get_user_role(request.user)
            if role == ROLE_ADMIN or role in allowed_roles:
                return view_func(request, *args, **kwargs)
            messages.error(request, "Ban khong co quyen truy cap khu vuc nay.")
            return redirect("/dashboard/")

        return _wrapped

    return decorator


def admin_required(view_func):
    @login_required(login_url="/auth/login/")
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        token_ok, token_error = _ensure_session_token(request)
        if not token_ok:
            messages.error(request, token_error or "Phien dang nhap het han. Vui long dang nhap lai.")
            return redirect("/auth/logout/")

        if _get_user_role(request.user) == ROLE_ADMIN:
            return view_func(request, *args, **kwargs)
        messages.error(request, "Chi admin moi co quyen truy cap khu vuc nay.")
        return redirect("/dashboard/")

    return _wrapped


def login_view(request):
    _ensure_role_groups()
    if request.user.is_authenticated:
        return redirect("/dashboard/")

    if request.method == "POST":
        client_key = request.META.get("REMOTE_ADDR", "unknown")
        if is_rate_limited(f"gateway-login:{client_key}", limit=25, window_seconds=300):
            messages.error(request, "Ban dang thu dang nhap qua nhieu lan. Vui long thu lai sau.")
            return render(request, "auth_login.html", _role_context(request.user))

        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")
        ok, data, error = _auth_request(
            "post",
            "/auth/login/",
            json={"username": username, "password": password},
        )
        if not ok:
            messages.error(request, "Tai khoan hoac mat khau khong dung.")
        else:
            user = _sync_local_user((data or {}).get("user", {}))
            if not user:
                messages.error(request, "Dang nhap that bai do du lieu nguoi dung khong hop le.")
                context = _role_context(request.user)
                return render(request, "auth_login.html", context)

            login(request, user)
            request.session["access_token"] = (data or {}).get("access_token")
            request.session["refresh_token"] = (data or {}).get("refresh_token")
            customer_id = _resolve_customer_id_for_email(user.email)
            if customer_id:
                request.session["customer_id"] = customer_id
            return redirect("/dashboard/")

    context = _role_context(request.user)
    return render(request, "auth_login.html", context)


def register_view(request):
    _ensure_role_groups()
    if request.user.is_authenticated:
        return redirect("/dashboard/")

    if request.method == "POST":
        full_name = request.POST.get("full_name", "").strip()
        username = request.POST.get("username", "").strip()
        email = request.POST.get("email", "").strip().lower()
        password = request.POST.get("password", "")
        confirm_password = request.POST.get("confirm_password", "")

        if not username or not email or not password:
            messages.error(request, "Vui long nhap day du thong tin bat buoc.")
            return render(request, "auth_register.html", _role_context(request.user))
        if password != confirm_password:
            messages.error(request, "Mat khau xac nhan khong khop.")
            return render(request, "auth_register.html", _role_context(request.user))
        auth_ok, auth_data, auth_error = _auth_request(
            "post",
            "/auth/register/",
            json={
                "username": username,
                "email": email,
                "password": password,
                "full_name": full_name,
                "role": ROLE_CUSTOMER,
            },
        )
        if not auth_ok:
            messages.error(request, auth_error or "Dang ky that bai.")
            return render(request, "auth_register.html", _role_context(request.user))

        user = _sync_local_user((auth_data or {}).get("user", {}))
        if not user:
            messages.error(request, "Dang ky that bai do du lieu nguoi dung khong hop le.")
            return render(request, "auth_register.html", _role_context(request.user))

        ok, data, error = _service_request(
            "post",
            f"{CUSTOMER_SERVICE_URL}/customers/",
            json={"name": full_name or username, "email": email},
        )

        login(request, user)
        request.session["access_token"] = (auth_data or {}).get("access_token")
        request.session["refresh_token"] = (auth_data or {}).get("refresh_token")
        if ok and isinstance(data, dict) and data.get("id"):
            request.session["customer_id"] = data.get("id")
        elif error:
            messages.warning(request, f"Da tao tai khoan, nhung dong bo customer that bai: {error}")

        messages.success(request, "Dang ky thanh cong. Chao mung ban den voi BookShop.")
        return redirect("/dashboard/")

    return render(request, "auth_register.html", _role_context(request.user))


@login_required(login_url="/auth/login/")
def logout_view(request):
    logout(request)
    request.session.pop("access_token", None)
    request.session.pop("refresh_token", None)
    return redirect("/auth/login/")


def _ensure_session_token(request):
    access_token = request.session.get("access_token")
    refresh_token = request.session.get("refresh_token")

    if not access_token:
        return False, "Thieu access token trong phien lam viec."

    verify_ok, _, _ = _auth_request("post", "/auth/verify/", json={"token": access_token})
    if verify_ok:
        return True, None

    if not refresh_token:
        return False, "Token het han va khong co refresh token."

    refresh_ok, refresh_data, refresh_error = _auth_request(
        "post",
        "/auth/refresh/",
        json={"refresh_token": refresh_token},
    )
    if not refresh_ok or not isinstance(refresh_data, dict):
        return False, refresh_error or "Khong refresh duoc token."

    new_access = refresh_data.get("access_token")
    new_refresh = refresh_data.get("refresh_token")
    if not new_access or not new_refresh:
        return False, "Du lieu token tra ve khong hop le."

    request.session["access_token"] = new_access
    request.session["refresh_token"] = new_refresh
    _sync_local_user((refresh_data or {}).get("user", {}))
    return True, None


@login_required(login_url="/auth/login/")
def dashboard(request):
    role = _get_user_role(request.user)
    if role in [ROLE_ADMIN, ROLE_STAFF]:
        return redirect("/staff/books/")
    if role == ROLE_CUSTOMER:
        return redirect("/shop/")

    messages.error(request, "Tai khoan chua duoc cap quyen. Vui long lien he quan tri vien.")
    return redirect("/auth/logout/")


def home(request):
    if request.user.is_authenticated:
        return redirect("/dashboard/")
    return redirect("/auth/login/")


@role_required(ROLE_STAFF)
def book_list(request):
    books, book_error = _get_list(f"{BOOK_SERVICE_URL}/books/")
    catalog_books, catalog_error = _get_list(f"{CATALOG_SERVICE_URL}/catalog/books/")
    customers, customer_error = _get_list(f"{CUSTOMER_SERVICE_URL}/customers/")

    customer_id = _resolve_int(request.GET.get("customer_id"), _default_customer_id(customers))
    selected_book_id = _resolve_int(request.GET.get("edit_book"), 0)
    selected_book = next((book for book in books if book.get("id") == selected_book_id), None)

    context = {
        "books": books,
        "catalog_books": catalog_books,
        "catalog_count": len(catalog_books),
        "customers": customers,
        "customer_id": customer_id,
        "selected_book": selected_book,
        "service_warnings": [warning for warning in [book_error, catalog_error, customer_error] if warning],
    }
    context.update(_role_context(request.user))
    return render(request, "books.html", context)


@role_required(ROLE_STAFF)
def save_book(request):
    if request.method != "POST":
        return redirect("/staff/books/")

    payload = {
        "title": request.POST.get("title", "").strip(),
        "author": request.POST.get("author", "").strip(),
        "category": request.POST.get("category", "sach").strip() or "sach",
        "description": request.POST.get("description", "").strip(),
        "image_url": request.POST.get("image_url", "").strip(),
        "price": request.POST.get("price", "0").strip(),
        "stock": request.POST.get("stock", "0").strip(),
    }
    book_id = request.POST.get("book_id")

    if book_id:
        ok, _, error = _service_request("put", f"{BOOK_SERVICE_URL}/books/{book_id}/", json=payload)
        if ok:
            messages.success(request, "Da cap nhat sach.")
        else:
            messages.error(request, error)
            return redirect(f"/staff/books/?edit_book={book_id}")
    else:
        ok, _, error = _service_request("post", f"{BOOK_SERVICE_URL}/books/", json=payload)
        if ok:
            messages.success(request, "Da them sach moi.")
        else:
            messages.error(request, error)
    return redirect("/staff/books/")


@role_required(ROLE_STAFF)
def update_book_price(request, book_id):
    if request.method != "POST":
        return redirect(f"/staff/books/?edit_book={book_id}")

    price = request.POST.get("price", "0").strip()
    ok, _, error = _service_request("put", f"{BOOK_SERVICE_URL}/books/{book_id}/price/", json={"price": price})
    if ok:
        _sync_catalog_silently()
        messages.success(request, "Da cap nhat gia sach.")
    else:
        messages.error(request, error)
    return redirect(f"/staff/books/?edit_book={book_id}")


@role_required(ROLE_STAFF)
def create_promotion(request, book_id):
    if request.method != "POST":
        return redirect(f"/staff/books/?edit_book={book_id}")

    payload = {
        "book": book_id,
        "name": request.POST.get("name", "").strip(),
        "discount_percent": _resolve_int(request.POST.get("discount_percent"), 0),
    }
    if not payload["name"]:
        messages.error(request, "Vui long nhap ten khuyen mai.")
        return redirect(f"/staff/books/?edit_book={book_id}")
    if payload["discount_percent"] <= 0 or payload["discount_percent"] > 100:
        messages.error(request, "Muc giam gia phai tu 1 den 100.")
        return redirect(f"/staff/books/?edit_book={book_id}")

    ok, _, error = _service_request("post", f"{BOOK_SERVICE_URL}/promotions/", json=payload)
    if ok:
        _sync_catalog_silently()
        messages.success(request, "Da them khuyen mai cho sach.")
    else:
        messages.error(request, error)
    return redirect(f"/staff/books/?edit_book={book_id}")


@role_required(ROLE_STAFF)
def delete_book(request, book_id):
    if request.method == "POST":
        ok, _, error = _service_request("delete", f"{BOOK_SERVICE_URL}/books/{book_id}/")
        if ok:
            messages.success(request, "Da xoa sach.")
        else:
            messages.error(request, error)
    return redirect("/staff/books/")


@role_required(ROLE_STAFF)
def sync_catalog(request):
    if request.method == "POST":
        ok, data, error = _service_request("post", f"{CATALOG_SERVICE_URL}/catalog/sync/")
        if ok:
            messages.success(request, f"Da dong bo {len(data or [])} sach vao catalog.")
        else:
            messages.error(request, error)
    return redirect("/staff/books/")


@role_required(ROLE_STAFF)
def customer_list(request):
    customers, customer_error = _get_list(f"{CUSTOMER_SERVICE_URL}/customers/")
    context = {
        "customers": customers,
        "customer_id": _resolve_int(request.GET.get("customer_id"), _default_customer_id(customers)),
        "service_warnings": [warning for warning in [customer_error] if warning],
    }
    context.update(_role_context(request.user))
    return render(request, "customers.html", context)


@role_required(ROLE_STAFF)
def create_customer(request):
    if request.method != "POST":
        return redirect("/customers/")

    payload = {
        "name": request.POST.get("name", "").strip(),
        "email": request.POST.get("email", "").strip(),
    }
    ok, data, error = _service_request("post", f"{CUSTOMER_SERVICE_URL}/customers/", json=payload)
    if ok:
        messages.success(request, "Da tao khach hang moi.")
        return redirect(f"/customer/cart/{data.get('id', 1)}/")
    messages.error(request, error)
    return redirect("/customers/")


@role_required(ROLE_CUSTOMER)
def cart_lookup(request):
    customer_id = _current_customer_id(request)
    return redirect(f"/customer/cart/{customer_id}/")


def _collect_service_health():
    checks = [
        ("book-service", f"{BOOK_SERVICE_URL}/health/"),
        ("fashion-service", f"{FASHION_SERVICE_URL}/health/"),
        ("household-service", f"{HOUSEHOLD_SERVICE_URL}/health/"),
        ("electronics-service", f"{ELECTRONICS_SERVICE_URL}/health/"),
        ("beauty-service", f"{BEAUTY_SERVICE_URL}/health/"),
        ("grocery-service", f"{GROCERY_SERVICE_URL}/health/"),
        ("sports-service", f"{SPORTS_SERVICE_URL}/health/"),
        ("cart-service", f"{CART_SERVICE_URL}/health/"),
        ("customer-service", f"{CUSTOMER_SERVICE_URL}/health/"),
        ("catalog-service", f"{CATALOG_SERVICE_URL}/health/"),
        ("order-service", f"{ORDER_SERVICE_URL}/health/"),
        ("aiservice", f"{AI_SERVICE_URL}/health/"),
        ("auth-service", f"{AUTH_SERVICE_URL}/health/"),
    ]
    results = [{"name": "api-gateway", "healthy": True, "detail": "ready"}]

    for name, url in checks:
        ok, data, error = _service_request("get", url)
        detail = "ok"
        if isinstance(data, dict):
            detail = data.get("status") or data.get("message") or detail
        if error:
            detail = error
        results.append({"name": name, "healthy": ok, "detail": detail})

    return results


def _serialize_users_with_roles():
    role_names = [ROLE_ADMIN, ROLE_STAFF, ROLE_CUSTOMER]
    users = []
    for user in User.objects.all().order_by("id"):
        role = _get_user_role(user) or "Unassigned"
        users.append(
            {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "is_superuser": user.is_superuser,
                "role": role,
                "joined_at": user.date_joined,
            }
        )

    return users, role_names


@role_required(ROLE_CUSTOMER)
def shop(request):
    customer_id = _current_customer_id(request)
    search_query = (request.GET.get("q") or "").strip().lower()
    selected_category = (request.GET.get("category") or "").strip().lower()
    normalized_search_query = _normalize_text(search_query)

    books, product_warnings = _fetch_all_products()
    all_products = list(books)
    semantic_error = None

    if search_query:
        semantic_payload, semantic_error = _search_semantic(search_query, top_k=80)
        semantic_rows = semantic_payload.get("results", []) if isinstance(semantic_payload, dict) else []

        if semantic_rows:
            rank_map = {
                _resolve_int(row.get("product_id"), 0): {
                    "rank": index,
                    "score": row.get("score", 0),
                }
                for index, row in enumerate(semantic_rows)
                if _resolve_int(row.get("product_id"), 0) > 0
            }

            books = [book for book in books if book.get("id") in rank_map]
            books.sort(key=lambda item: rank_map.get(item.get("id"), {}).get("rank", 9999))
            for book in books:
                book["semantic_score"] = rank_map.get(book.get("id"), {}).get("score", 0)
        else:
            books = [
                book
                for book in books
                if normalized_search_query in _normalize_text(book.get("title"))
                or normalized_search_query in _normalize_text(book.get("author"))
                or normalized_search_query in _normalize_text(book.get("description"))
            ]

    if selected_category and selected_category in CATEGORY_LABELS:
        books = [book for book in books if (book.get("category") or "sach") == selected_category]

    recommendation_ok, recommendation_data, recommendation_error = _service_request(
        "get",
        f"{RECOMMENDER_AI_SERVICE_URL}/recommendations/{customer_id}/",
    )
    recommended_ids = set()
    recommendations = []
    if recommendation_ok and isinstance(recommendation_data, dict):
        recommendations = _normalize_recommendations(recommendation_data.get("recommendations", []), all_products)
        for item in recommendations:
            raw_book_id = item.get("book_id")
            normalized_id = _resolve_int(raw_book_id, 0)
            if normalized_id <= 0:
                continue

            if normalized_id >= PRODUCT_ID_OFFSETS["sach"]:
                recommended_ids.add(normalized_id)
            else:
                recommended_ids.add(_encode_product_id("sach", normalized_id))
                recommended_ids.add(normalized_id)

    cart_ok, cart_data, cart_error = _service_request("get", f"{CART_SERVICE_URL}/carts/{customer_id}/")
    cart_payload = cart_data if cart_ok and isinstance(cart_data, dict) else {"items": []}
    cart_items = cart_payload.get("items", [])
    total_quantity, total_price = _enrich_cart_items(cart_items, all_products)
    favorite_ids = _favorite_ids(request)
    for book in books:
        book["category_label"] = CATEGORY_LABELS.get(book.get("category"), "Khac")

    search_triggered = bool(search_query)
    search_result_preview = books[:8] if search_triggered else []
    cart_preview_items = cart_items[:6]

    context = {
        "customer_id": customer_id,
        "books": books,
        "category_choices": CATEGORY_LABELS,
        "selected_category": selected_category,
        "recommendations": recommendations,
        "recommended_ids": recommended_ids,
        "search_query": request.GET.get("q", "").strip(),
        "favorite_ids": favorite_ids,
        "favorite_count": len(favorite_ids),
        "cart_id": cart_payload.get("cart_id"),
        "item_count": len(cart_items),
        "total_quantity": total_quantity,
        "total_price": total_price,
        "search_triggered": search_triggered,
        "search_result_preview": search_result_preview,
        "cart_preview_items": cart_preview_items,
        "service_warnings": [
            warning
            for warning in [*product_warnings, recommendation_error, semantic_error, cart_error]
            if warning
        ],
        "chat_suggestions": [
            "top sản phẩm bán chạy",
            "chuỗi hành vi phổ biến của khách hàng",
            "funnel của sản phẩm P0001",
        ],
    }
    context.update(_role_context(request.user))
    return render(request, "shop.html", context)


@role_required(ROLE_CUSTOMER)
def chat_advice(request):
    if request.method != "POST":
        return JsonResponse({"error": "Phương thức không được hỗ trợ."}, status=405)

    try:
        payload = json.loads((request.body or b"{}").decode("utf-8"))
    except (UnicodeDecodeError, ValueError):
        payload = {}

    query = str(payload.get("query") or "").strip()
    if len(query) < 2:
        return JsonResponse({"error": "Vui lòng nhập câu hỏi hợp lệ."}, status=400)

    customer_id = _current_customer_id(request)
    data, error = _chatbot_advice(customer_id=customer_id, query=query)
    if error:
        return JsonResponse({"error": error}, status=503)

    return JsonResponse(data)


@role_required(ROLE_CUSTOMER)
def product_detail(request, product_id):
    customer_id = _current_customer_id(request)
    ok, product, error = _fetch_product_detail_by_id(product_id)
    if not ok or not isinstance(product, dict):
        messages.error(request, error or "Khong tim thay san pham.")
        return redirect("/shop/")

    books, _ = _fetch_all_products()

    cart_ok, cart_data, cart_error = _service_request("get", f"{CART_SERVICE_URL}/carts/{customer_id}/")
    cart_payload = cart_data if cart_ok and isinstance(cart_data, dict) else {"items": []}
    items = cart_payload.get("items", [])
    total_quantity, total_price = _enrich_cart_items(items, books)
    favorite_ids = _favorite_ids(request)
    insights, insights_error = _review_insights(book_id=product.get("id"))

    context = {
        "customer_id": customer_id,
        "product": product,
        "category_label": CATEGORY_LABELS.get(product.get("category"), "Khac"),
        "is_favorite": product.get("id") in favorite_ids,
        "favorite_count": len(favorite_ids),
        "cart_id": cart_payload.get("cart_id"),
        "item_count": len(items),
        "total_quantity": total_quantity,
        "total_price": total_price,
        "review_insights": insights,
        "service_warnings": [warning for warning in [cart_error, insights_error] if warning],
    }
    context.update(_role_context(request.user))
    return render(request, "product_detail.html", context)


@role_required(ROLE_CUSTOMER)
def toggle_favorite(request, product_id):
    customer_id = _current_customer_id(request)
    if request.method != "POST":
        return redirect("/shop/")

    normalized_product_id = product_id
    if normalized_product_id < PRODUCT_ID_OFFSETS["sach"]:
        normalized_product_id = _encode_product_id("sach", normalized_product_id)

    favorite_ids = _favorite_ids(request)
    if normalized_product_id in favorite_ids:
        favorite_ids = [item for item in favorite_ids if item != normalized_product_id]
        messages.success(request, "Da bo khoi muc yeu thich.")
    else:
        favorite_ids.append(normalized_product_id)
        messages.success(request, "Da them vao muc yeu thich.")

    _save_favorite_ids(request, favorite_ids)
    next_url = request.POST.get("next") or f"/customer/{customer_id}/favorites/"
    return redirect(next_url)


@role_required(ROLE_CUSTOMER)
def favorite_products(request, customer_id):
    resolved_customer_id = _current_customer_id(request, customer_id)
    books, product_warnings = _fetch_all_products()
    favorite_ids = _favorite_ids(request)
    favorites = [book for book in books if book.get("id") in favorite_ids]
    for product in favorites:
        product["category_label"] = CATEGORY_LABELS.get(product.get("category"), "Khac")

    context = {
        "customer_id": resolved_customer_id,
        "favorites": favorites,
        "favorite_count": len(favorites),
        "service_warnings": [warning for warning in product_warnings if warning],
    }
    context.update(_role_context(request.user))
    return render(request, "favorites.html", context)


def _build_workspace(customer_id):
    customers, customer_error = _get_list(f"{CUSTOMER_SERVICE_URL}/customers/")
    books, product_warnings = _fetch_all_products()
    orders_ok, orders_data, order_error = _service_request("get", f"{ORDER_SERVICE_URL}/orders/")
    purchased_ok, purchased_data, purchased_error = _service_request(
        "get",
        f"{ORDER_SERVICE_URL}/customers/{customer_id}/purchased-books/",
    )
    reviews_ok, reviews_data, review_error = _service_request(
        "get",
        f"{COMMENT_RATE_SERVICE_URL}/reviews/",
        params={"customer_id": customer_id},
    )
    recommendation_ok, recommendation_data, recommendation_error = _service_request(
        "get",
        f"{RECOMMENDER_AI_SERVICE_URL}/recommendations/{customer_id}/",
    )
    insights_data, insights_error = _review_insights()
    cart_ok, cart_data, cart_error = _service_request("get", f"{CART_SERVICE_URL}/carts/{customer_id}/")

    customer = next((item for item in customers if item.get("id") == customer_id), None)
    cart_payload = cart_data if cart_ok and isinstance(cart_data, dict) else {"customer_id": customer_id, "items": []}
    items = cart_payload.get("items", [])
    total_quantity, total_price = _enrich_cart_items(items, books)

    orders = []
    if orders_ok and isinstance(orders_data, list):
        orders = [order for order in orders_data if order.get("customer_id") == customer_id]
        for order in orders:
            order["order_items"] = order.get("items", [])

    reviews = reviews_data if reviews_ok and isinstance(reviews_data, list) else []
    recommendations = []
    if recommendation_ok and isinstance(recommendation_data, dict):
        recommendations = _normalize_recommendations(recommendation_data.get("recommendations", []), books)
    purchased_ids = purchased_data.get("book_ids", []) if purchased_ok and isinstance(purchased_data, dict) else []
    purchased_set = {_resolve_int(item, 0) for item in purchased_ids}
    reviewable_books = [
        book
        for book in books
        if book.get("id") in purchased_set
        or (
            book.get("category") == "sach"
            and _resolve_int(book.get("local_id"), 0) in purchased_set
        )
    ]

    return {
        "customer_id": customer_id,
        "customer": customer,
        "customers": customers,
        "books": books,
        "items": items,
        "cart_id": cart_payload.get("cart_id"),
        "item_count": len(items),
        "total_quantity": total_quantity,
        "total_price": total_price,
        "orders": orders,
        "reviews": reviews,
        "reviewable_books": reviewable_books,
        "recommendations": recommendations,
        "order_count": len(orders),
        "review_count": len(reviews),
        "review_insights": insights_data,
        "service_warnings": [
            warning
            for warning in [customer_error, *product_warnings, order_error, purchased_error, review_error, recommendation_error, insights_error, cart_error]
            if warning
        ],
    }


@role_required(ROLE_CUSTOMER)
def view_cart(request, customer_id):
    resolved_customer_id = _current_customer_id(request, customer_id)
    context = _build_workspace(resolved_customer_id)
    context.update(_role_context(request.user))
    return render(request, "cart.html", context)


@admin_required
def admin_users(request):
    _ensure_role_groups()

    if request.method == "POST":
        user_id = _resolve_int(request.POST.get("user_id"), 0)
        role = request.POST.get("role", "").strip()
        if role not in [ROLE_ADMIN, ROLE_STAFF, ROLE_CUSTOMER]:
            messages.error(request, "Role khong hop le.")
            return redirect("/admin/users/")

        target = User.objects.filter(id=user_id).first()
        if not target:
            messages.error(request, "Khong tim thay nguoi dung.")
            return redirect("/admin/users/")

        if target.is_superuser:
            messages.warning(request, "Tai khoan superuser mac dinh la Admin.")
            return redirect("/admin/users/")

        sync_ok, _, sync_error = _auth_request(
            "post",
            "/auth/users/role/",
            json={"username": target.username, "role": role},
            headers={"X-Admin-Token": AUTH_ADMIN_TOKEN},
        )
        if not sync_ok:
            messages.error(request, f"Khong dong bo duoc role voi auth-service: {sync_error}")
            return redirect("/admin/users/")

        groups = Group.objects.filter(name__in=[ROLE_ADMIN, ROLE_STAFF, ROLE_CUSTOMER])
        target.groups.remove(*groups)
        target.groups.add(Group.objects.get(name=role))
        messages.success(request, f"Da cap role {role} cho {target.username}.")
        return redirect("/admin/users/")

    users, role_names = _serialize_users_with_roles()
    context = {
        "users": users,
        "role_names": role_names,
    }
    context.update(_role_context(request.user))
    return render(request, "admin_users.html", context)


@role_required(ROLE_STAFF)
def ai_dashboard(request):
    if request.method == "POST":
        action = (request.POST.get("action") or "").strip().lower()
        if action == "retrain":
            retrain_ok, retrain_data, retrain_error = _service_request(
                "post",
                f"{RECOMMENDER_AI_SERVICE_URL}/ai/retrain/",
                json={},
            )
            if retrain_ok:
                messages.success(request, "Da trigger retrain cho aiservice.")
            else:
                messages.error(request, retrain_error or "Khong trigger duoc retrain.")
            return redirect("/staff/ai/dashboard/")

    reviews_ok, reviews_data, review_error = _service_request("get", f"{COMMENT_RATE_SERVICE_URL}/reviews/")
    insight_data, insight_error = _review_insights()
    model_ok, model_data, model_error = _service_request("get", f"{COMMENT_RATE_SERVICE_URL}/reviews/model-status/")
    drift_ok, drift_data, drift_error = _service_request("get", f"{RECOMMENDER_AI_SERVICE_URL}/ai/drift/")
    products, product_warnings = _fetch_all_products()

    review_rows = reviews_data if reviews_ok and isinstance(reviews_data, list) else []
    product_map = {}
    for item in products:
        product_id = item.get("id")
        if product_id:
            product_map[product_id] = item

        if item.get("category") == "sach" and item.get("local_id"):
            product_map[item.get("local_id")] = item

    trend_rows = _weekly_sentiment_trend(review_rows)
    quality_alerts = _quality_alerts(review_rows, product_map)

    context = {
        "review_insights": insight_data if isinstance(insight_data, dict) else {},
        "model_status": model_data if model_ok and isinstance(model_data, dict) else {},
        "drift_status": drift_data if drift_ok and isinstance(drift_data, dict) else {},
        "weekly_trend": trend_rows,
        "quality_alerts": quality_alerts,
        "service_warnings": [
            warning
            for warning in [review_error, insight_error, model_error, drift_error, *product_warnings]
            if warning
        ],
    }
    context.update(_role_context(request.user))
    return render(request, "ai_dashboard.html", context)


@role_required(ROLE_STAFF)
def service_health(request):
    checks = _collect_service_health()
    total = len(checks)
    healthy = len([item for item in checks if item.get("healthy")])

    context = {
        "checks": checks,
        "healthy_count": healthy,
        "degraded_count": total - healthy,
        "gateway_metrics": metrics_snapshot(),
        "recent_traces": traces_snapshot(12),
    }
    context.update(_role_context(request.user))
    return render(request, "service_health.html", context)


@role_required(ROLE_STAFF)
def ops_metrics(request):
    return JsonResponse(metrics_snapshot())


@role_required(ROLE_STAFF)
def ops_traces(request):
    return JsonResponse({"traces": traces_snapshot(50)})


@role_required(ROLE_CUSTOMER)
def add_cart_item(request, customer_id):
    customer_id = _current_customer_id(request, customer_id)
    if request.method != "POST":
        return redirect(f"/customer/cart/{customer_id}/")

    cart_url = f"/customer/cart/{customer_id}/"
    next_url = (request.POST.get("next") or request.META.get("HTTP_REFERER") or "").strip()
    if not next_url.startswith("/"):
        next_url = cart_url

    cart_id = _resolve_int(request.POST.get("cart_id"), 0)
    if cart_id <= 0:
        cart_id, cart_error = _ensure_cart(customer_id)
        if not cart_id:
            messages.error(request, cart_error)
            return redirect(next_url)

    payload = {
        "cart": cart_id,
        "book_id": _resolve_int(request.POST.get("book_id"), 0),
        "quantity": _resolve_int(request.POST.get("quantity"), 1),
    }
    if payload["book_id"] <= 0:
        messages.error(request, "Vui long chon sach hop le.")
        return redirect(next_url)
    if payload["quantity"] <= 0:
        messages.error(request, "So luong phai lon hon 0.")
        return redirect(next_url)

    ok, _, error = _service_request("post", f"{CART_SERVICE_URL}/cart-items/", json=payload)
    if ok:
        if next_url != cart_url:
            messages.success(request, "Da them san pham vao gio hang.", extra_tags="cart-modal")
        else:
            messages.success(request, "Da them san pham vao gio hang.")
    else:
        messages.error(request, error)
    return redirect(next_url)


@role_required(ROLE_CUSTOMER)
def update_cart_item(request, customer_id, item_id):
    customer_id = _current_customer_id(request, customer_id)
    if request.method != "POST":
        return redirect(f"/customer/cart/{customer_id}/")

    quantity = _resolve_int(request.POST.get("quantity"), 1)
    if quantity <= 0:
        return delete_cart_item(request, customer_id, item_id)

    ok, _, error = _service_request("put", f"{CART_SERVICE_URL}/cart-items/{item_id}/", json={"quantity": quantity})
    if ok:
        messages.success(request, "Da cap nhat so luong.")
    else:
        messages.error(request, error)
    return redirect(f"/customer/cart/{customer_id}/")


@role_required(ROLE_CUSTOMER)
def delete_cart_item(request, customer_id, item_id):
    customer_id = _current_customer_id(request, customer_id)
    if request.method == "POST":
        ok, _, error = _service_request("delete", f"{CART_SERVICE_URL}/cart-items/{item_id}/")
        if ok:
            messages.success(request, "Da xoa san pham khoi gio hang.")
        else:
            messages.error(request, error)
    return redirect(f"/customer/cart/{customer_id}/")


@role_required(ROLE_CUSTOMER)
def create_order(request, customer_id):
    customer_id = _current_customer_id(request, customer_id)
    if request.method != "POST":
        return redirect(f"/customer/cart/{customer_id}/")

    cart_id, cart_error = _ensure_cart(customer_id)
    if not cart_id:
        messages.error(request, cart_error)
        return redirect(f"/customer/cart/{customer_id}/")

    payload = {
        "customer_id": customer_id,
        "payment_method": request.POST.get("payment_method", "cod"),
        "shipping_method": request.POST.get("shipping_method", "standard"),
        "shipping_address": request.POST.get("shipping_address", "").strip(),
    }
    ok, _, error = _service_request("post", f"{ORDER_SERVICE_URL}/orders/", json=payload)
    if ok:
        messages.success(request, "Da tao don hang.")
    else:
        messages.error(request, error)
    return redirect(f"/customer/cart/{customer_id}/")


@role_required(ROLE_CUSTOMER)
def create_review(request, customer_id):
    customer_id = _current_customer_id(request, customer_id)
    if request.method != "POST":
        return redirect(f"/customer/cart/{customer_id}/")

    payload = {
        "customer_id": customer_id,
        "book_id": _resolve_int(request.POST.get("book_id"), 0),
        "rating": _resolve_int(request.POST.get("rating"), 5),
        "comment": request.POST.get("comment", "").strip(),
    }
    if payload["book_id"] <= 0:
        messages.error(request, "Vui long chon san pham de danh gia.")
        return redirect(f"/customer/cart/{customer_id}/")
    if payload["rating"] < 1 or payload["rating"] > 5:
        messages.error(request, "Diem danh gia phai tu 1 den 5.")
        return redirect(f"/customer/cart/{customer_id}/")

    ok, _, error = _service_request("post", f"{COMMENT_RATE_SERVICE_URL}/reviews/", json=payload)
    if ok:
        messages.success(request, "Da gui danh gia.")
    else:
        messages.error(request, error)
    return redirect(f"/customer/cart/{customer_id}/")