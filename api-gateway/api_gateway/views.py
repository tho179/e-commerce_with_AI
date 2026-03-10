from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.shortcuts import redirect, render
import requests

BOOK_SERVICE_URL = "http://book-service:8000"
CART_SERVICE_URL = "http://cart-service:8000"
CUSTOMER_SERVICE_URL = "http://customer-service:8000"
CATALOG_SERVICE_URL = "http://catalog-service:8000"
ORDER_SERVICE_URL = "http://order-service:8000"
COMMENT_RATE_SERVICE_URL = "http://comment-rate-service:8000"
RECOMMENDER_AI_SERVICE_URL = "http://recommender-ai-service:8000"
REQUEST_TIMEOUT = 5


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


def _service_request(method, url, **kwargs):
    try:
        response = requests.request(method, url, timeout=REQUEST_TIMEOUT, **kwargs)
    except requests.RequestException:
        return False, None, "Khong the ket noi service."

    data = None
    if response.content:
        try:
            data = response.json()
        except ValueError:
            data = None

    if not response.ok:
        if isinstance(data, dict) and data.get("error"):
            return False, data, data["error"]
        return False, data, f"Yeu cau that bai ({response.status_code})."

    return True, data, None


def _get_list(url, params=None):
    ok, data, error = _service_request("get", url, params=params)
    if ok and isinstance(data, list):
        return data, None
    return [], error


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


def _enrich_cart_items(items, books):
    books_by_id = {book.get("id"): book for book in books}
    total_quantity = 0
    total_price = Decimal("0")

    for item in items:
        quantity = int(item.get("quantity", 0) or 0)
        book = books_by_id.get(item.get("book_id"), {})
        price = _to_decimal(book.get("effective_price", book.get("price", item.get("price", 0))))
        item["book_title"] = book.get("title") or f"Sach #{item.get('book_id', '?')}"
        item["price"] = price
        item["line_total"] = price * quantity
        total_quantity += quantity
        total_price += item["line_total"]

    return total_quantity, total_price


def _sync_catalog_silently():
    ok, _, error = _service_request("post", f"{CATALOG_SERVICE_URL}/catalog/sync/")
    return ok, error


def home(request):
    return redirect("/customers/")


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
    return render(request, "books.html", context)


def save_book(request):
    if request.method != "POST":
        return redirect("/staff/books/")

    payload = {
        "title": request.POST.get("title", "").strip(),
        "author": request.POST.get("author", "").strip(),
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


def delete_book(request, book_id):
    if request.method == "POST":
        ok, _, error = _service_request("delete", f"{BOOK_SERVICE_URL}/books/{book_id}/")
        if ok:
            messages.success(request, "Da xoa sach.")
        else:
            messages.error(request, error)
    return redirect("/staff/books/")


def sync_catalog(request):
    if request.method == "POST":
        ok, data, error = _service_request("post", f"{CATALOG_SERVICE_URL}/catalog/sync/")
        if ok:
            messages.success(request, f"Da dong bo {len(data or [])} sach vao catalog.")
        else:
            messages.error(request, error)
    return redirect("/staff/books/")


def customer_list(request):
    customers, customer_error = _get_list(f"{CUSTOMER_SERVICE_URL}/customers/")
    context = {
        "customers": customers,
        "customer_id": _resolve_int(request.GET.get("customer_id"), _default_customer_id(customers)),
        "service_warnings": [warning for warning in [customer_error] if warning],
    }
    return render(request, "customers.html", context)


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


def cart_lookup(request):
    customers, _ = _get_list(f"{CUSTOMER_SERVICE_URL}/customers/")
    customer_id = _resolve_int(request.GET.get("customer_id"), _default_customer_id(customers))
    return redirect(f"/customer/cart/{customer_id}/")


def _build_workspace(customer_id):
    customers, customer_error = _get_list(f"{CUSTOMER_SERVICE_URL}/customers/")
    books, book_error = _get_list(f"{BOOK_SERVICE_URL}/books/")
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
    recommendations = recommendation_data.get("recommendations", []) if recommendation_ok and isinstance(recommendation_data, dict) else []
    purchased_ids = purchased_data.get("book_ids", []) if purchased_ok and isinstance(purchased_data, dict) else []
    reviewable_books = [book for book in books if book.get("id") in purchased_ids]

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
        "service_warnings": [warning for warning in [customer_error, book_error, order_error, purchased_error, review_error, recommendation_error, cart_error] if warning],
    }


def view_cart(request, customer_id):
    return render(request, "cart.html", _build_workspace(customer_id))


def add_cart_item(request, customer_id):
    if request.method != "POST":
        return redirect(f"/customer/cart/{customer_id}/")

    cart_id = _resolve_int(request.POST.get("cart_id"), 0)
    if cart_id <= 0:
        cart_id, cart_error = _ensure_cart(customer_id)
        if not cart_id:
            messages.error(request, cart_error)
            return redirect(f"/customer/cart/{customer_id}/")

    payload = {
        "cart": cart_id,
        "book_id": _resolve_int(request.POST.get("book_id"), 0),
        "quantity": _resolve_int(request.POST.get("quantity"), 1),
    }
    if payload["book_id"] <= 0:
        messages.error(request, "Vui long chon sach hop le.")
        return redirect(f"/customer/cart/{customer_id}/")
    if payload["quantity"] <= 0:
        messages.error(request, "So luong phai lon hon 0.")
        return redirect(f"/customer/cart/{customer_id}/")

    ok, _, error = _service_request("post", f"{CART_SERVICE_URL}/cart-items/", json=payload)
    if ok:
        messages.success(request, "Da them sach vao gio hang.")
    else:
        messages.error(request, error)
    return redirect(f"/customer/cart/{customer_id}/")


def update_cart_item(request, customer_id, item_id):
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


def delete_cart_item(request, customer_id, item_id):
    if request.method == "POST":
        ok, _, error = _service_request("delete", f"{CART_SERVICE_URL}/cart-items/{item_id}/")
        if ok:
            messages.success(request, "Da xoa san pham khoi gio hang.")
        else:
            messages.error(request, error)
    return redirect(f"/customer/cart/{customer_id}/")


def create_order(request, customer_id):
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


def create_review(request, customer_id):
    if request.method != "POST":
        return redirect(f"/customer/cart/{customer_id}/")

    payload = {
        "customer_id": customer_id,
        "book_id": _resolve_int(request.POST.get("book_id"), 0),
        "rating": _resolve_int(request.POST.get("rating"), 5),
        "comment": request.POST.get("comment", "").strip(),
    }
    if payload["book_id"] <= 0:
        messages.error(request, "Vui long chon sach de danh gia.")
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