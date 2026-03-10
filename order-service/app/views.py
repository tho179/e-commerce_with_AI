from decimal import Decimal

import requests
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Order, OrderItem
from .serializers import OrderSerializer

CART_SERVICE_URL = "http://cart-service:8000"
BOOK_SERVICE_URL = "http://book-service:8000"
PAY_SERVICE_URL = "http://pay-service:8000"
SHIP_SERVICE_URL = "http://ship-service:8000"


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
            cart_response = requests.get(f"{CART_SERVICE_URL}/carts/{customer_id}/", timeout=5)
            books_response = requests.get(f"{BOOK_SERVICE_URL}/books/", timeout=5)
            cart_response.raise_for_status()
            books_response.raise_for_status()
        except requests.RequestException:
            return Response({"error": "Dependency unavailable"}, status=503)

        cart_data = cart_response.json()
        items = cart_data.get("items", [])
        if not items:
            return Response({"error": "Cart is empty"}, status=400)

        books_by_id = {book["id"]: book for book in books_response.json()}
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
            book = books_by_id.get(item["book_id"])
            if not book:
                order.status = "failed"
                order.save(update_fields=["status"])
                return Response({"error": f"Book {item['book_id']} not found"}, status=400)
            price = Decimal(str(book.get("effective_price", book["price"])))
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
            )
            shipment_response.raise_for_status()
        except requests.RequestException:
            if payment_response is not None and payment_response.ok:
                payment_id = payment_response.json().get("id")
                requests.post(f"{PAY_SERVICE_URL}/payments/{payment_id}/cancel/", timeout=5)
            if shipment_response is not None and shipment_response.ok:
                shipment_id = shipment_response.json().get("id")
                requests.post(f"{SHIP_SERVICE_URL}/shipments/{shipment_id}/cancel/", timeout=5)
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