from decimal import Decimal
import os

import requests
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Order, OrderItem
from .serializers import OrderSerializer

CART_SERVICE_URL = "http://cart-service:8000"
BOOK_SERVICE_URL = "http://book-service:8000"
FASHION_SERVICE_URL = "http://fashion-service:8000"
HOUSEHOLD_SERVICE_URL = "http://household-service:8000"
ELECTRONICS_SERVICE_URL = "http://electronics-service:8000"
PAY_SERVICE_URL = "http://pay-service:8000"
SHIP_SERVICE_URL = "http://ship-service:8000"
SERVICE_SHARED_TOKEN = os.getenv("SERVICE_SHARED_TOKEN", "")

PRODUCT_ID_OFFSETS = {
    "sach": 1000000,
    "quan_ao": 2000000,
    "gia_dung": 3000000,
    "dien_tu": 4000000,
}

PRODUCT_SOURCES = {
    "sach": {"base_url": BOOK_SERVICE_URL, "list_path": "/books/"},
    "quan_ao": {"base_url": FASHION_SERVICE_URL, "list_path": "/products/"},
    "gia_dung": {"base_url": HOUSEHOLD_SERVICE_URL, "list_path": "/products/"},
    "dien_tu": {"base_url": ELECTRONICS_SERVICE_URL, "list_path": "/products/"},
}


def _internal_headers():
    if not SERVICE_SHARED_TOKEN:
        return {}
    return {"X-Service-Token": SERVICE_SHARED_TOKEN}


def _encode_product_id(category, local_id):
    return PRODUCT_ID_OFFSETS.get(category, 0) + int(local_id)


def _fetch_product_price_map():
    products = {}
    headers = _internal_headers()
    for category, source in PRODUCT_SOURCES.items():
        response = requests.get(
            f"{source['base_url']}{source['list_path']}",
            timeout=5,
            headers=headers,
        )
        response.raise_for_status()
        rows = response.json() if isinstance(response.json(), list) else []
        for row in rows:
            local_id = int(row.get("id", 0))
            if local_id <= 0:
                continue
            global_id = _encode_product_id(category, local_id)
            products[global_id] = Decimal(str(row.get("effective_price", row.get("price", 0))))
            if category == "sach":
                products[local_id] = products[global_id]
    return products


class HealthCheck(APIView):
    def get(self, request):
        return Response({"service": "order-service", "status": "ok"})


class OrderListCreate(APIView):
    def get(self, request):
        serializer = OrderSerializer(Order.objects.all(), many=True)
        return Response(serializer.data)

    def post(self, request):
        customer_id = request.data.get("customer_id")
        payment_method = request.data.get("payment_method", "cod")
        shipping_method = request.data.get("shipping_method", "standard")
        shipping_address = request.data.get("shipping_address", "Unknown")

        try:
            cart_response = requests.get(
                f"{CART_SERVICE_URL}/carts/{customer_id}/",
                timeout=5,
                headers=_internal_headers(),
            )
            cart_response.raise_for_status()
            products_by_id = _fetch_product_price_map()
        except requests.RequestException:
            return Response({"error": "Dependency unavailable"}, status=503)

        cart_data = cart_response.json()
        items = cart_data.get("items", [])
        if not items:
            return Response({"error": "Cart is empty"}, status=400)

        order = Order.objects.create(
            customer_id=customer_id,
            cart_id=cart_data.get("cart_id", 0),
            payment_method=payment_method,
            shipping_method=shipping_method,
            shipping_address=shipping_address,
            status="pending",
        )

        total_amount = Decimal("0")
        for item in items:
            product_id = item.get("book_id")
            price = products_by_id.get(product_id)
            if price is None:
                order.status = "failed"
                order.save(update_fields=["status"])
                return Response({"error": f"Product {item['book_id']} not found"}, status=400)
            OrderItem.objects.create(
                order=order,
                book_id=item["book_id"],
                quantity=item["quantity"],
                price=price,
            )
            total_amount += price * item["quantity"]

        order.total_amount = total_amount
        order.save(update_fields=["total_amount"])

        payment_response = None
        shipment_response = None
        try:
            payment_response = requests.post(
                f"{PAY_SERVICE_URL}/payments/reserve/",
                json={
                    "order_id": order.id,
                    "customer_id": customer_id,
                    "amount": str(total_amount),
                    "method": payment_method,
                },
                timeout=5,
                headers=_internal_headers(),
            )
            payment_response.raise_for_status()

            shipment_response = requests.post(
                f"{SHIP_SERVICE_URL}/shipments/reserve/",
                json={
                    "order_id": order.id,
                    "customer_id": customer_id,
                    "address": shipping_address,
                    "method": shipping_method,
                },
                timeout=5,
                headers=_internal_headers(),
            )
            shipment_response.raise_for_status()
        except requests.RequestException:
            if payment_response is not None and payment_response.ok:
                payment_id = payment_response.json().get("id")
                requests.post(
                    f"{PAY_SERVICE_URL}/payments/{payment_id}/cancel/",
                    timeout=5,
                    headers=_internal_headers(),
                )
            if shipment_response is not None and shipment_response.ok:
                shipment_id = shipment_response.json().get("id")
                requests.post(
                    f"{SHIP_SERVICE_URL}/shipments/{shipment_id}/cancel/",
                    timeout=5,
                    headers=_internal_headers(),
                )
            order.status = "failed"
            order.save(update_fields=["status"])
            return Response({"error": "Order orchestration failed"}, status=502)

        order.payment_reference = str(payment_response.json().get("id", ""))
        order.shipment_reference = str(shipment_response.json().get("id", ""))
        order.status = "confirmed"
        order.save(update_fields=["payment_reference", "shipment_reference", "status"])
        return Response(OrderSerializer(order).data, status=201)


class PurchasedBooksView(APIView):
    def get(self, request, customer_id):
        purchased = {}
        orders = Order.objects.filter(customer_id=customer_id, status="confirmed").prefetch_related("items")
        for order in orders:
            for item in order.items.all():
                entry = purchased.setdefault(item.book_id, {"book_id": item.book_id, "quantity": 0, "order_ids": []})
                entry["quantity"] += item.quantity
                entry["order_ids"].append(order.id)

        books = list(purchased.values())
        return Response({
            "customer_id": customer_id,
            "book_ids": [item["book_id"] for item in books],
            "books": books,
        })


class PurchasedBookDetailView(APIView):
    def get(self, request, customer_id, book_id):
        order_items = OrderItem.objects.filter(
            order__customer_id=customer_id,
            order__status="confirmed",
            book_id=book_id,
        ).select_related("order")
        return Response({
            "customer_id": customer_id,
            "book_id": book_id,
            "purchased": order_items.exists(),
            "order_ids": [item.order_id for item in order_items],
            "quantity": sum(item.quantity for item in order_items),
        })