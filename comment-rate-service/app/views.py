import requests
import os
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Review
from .serializers import ReviewSerializer

ORDER_SERVICE_URL = "http://order-service:8000"
SERVICE_SHARED_TOKEN = os.getenv("SERVICE_SHARED_TOKEN", "")


def _internal_headers():
    if not SERVICE_SHARED_TOKEN:
        return {}
    return {"X-Service-Token": SERVICE_SHARED_TOKEN}


class HealthCheck(APIView):
    def get(self, request):
        return Response({"service": "comment-rate-service", "status": "ok"})


class ReviewListCreate(APIView):
    def get(self, request):
        queryset = Review.objects.all()
        book_id = request.GET.get("book_id")
        customer_id = request.GET.get("customer_id")
        if book_id:
            queryset = queryset.filter(book_id=book_id)
        if customer_id:
            queryset = queryset.filter(customer_id=customer_id)
        serializer = ReviewSerializer(queryset, many=True)
        return Response(serializer.data)

    def post(self, request):
        customer_id = request.data.get("customer_id")
        book_id = request.data.get("book_id")
        try:
            purchase_response = requests.get(
                f"{ORDER_SERVICE_URL}/customers/{customer_id}/purchased-books/{book_id}/",
                timeout=5,
                headers=_internal_headers(),
            )
            purchase_response.raise_for_status()
        except requests.RequestException:
            return Response({"error": "Dependency unavailable"}, status=503)

        if not purchase_response.json().get("purchased"):
            return Response({"error": "Ban chi co the danh gia sach da mua."}, status=400)

        existing_review = Review.objects.filter(customer_id=customer_id, book_id=book_id).first()
        serializer = ReviewSerializer(existing_review, data=request.data, partial=bool(existing_review)) if existing_review else ReviewSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=400)