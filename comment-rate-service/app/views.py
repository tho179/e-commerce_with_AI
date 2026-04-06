import requests
import os
from rest_framework.response import Response
from rest_framework.views import APIView

from .ai_review_engine import ANALYZER, analyze_review, summarize_reviews
from .event_bus import publish_review_event
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
            return Response({"error": "Ban chi co the danh gia san pham da mua."}, status=400)

        existing_review = Review.objects.filter(customer_id=customer_id, book_id=book_id).first()
        serializer = ReviewSerializer(existing_review, data=request.data, partial=bool(existing_review)) if existing_review else ReviewSerializer(data=request.data)
        if serializer.is_valid():
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
        return Response(serializer.errors, status=400)


class ReviewInsights(APIView):
    def get(self, request):
        queryset = Review.objects.all()
        book_id = request.GET.get("book_id")
        if book_id:
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
        summary["book_id"] = int(book_id) if str(book_id).isdigit() else None
        summary["scope"] = "book" if book_id else "global"
        return Response(summary)


class ReviewModelStatus(APIView):
    def get(self, request):
        review_count = Review.objects.count()
        status = ANALYZER.status()
        status["current_review_count"] = review_count
        return Response(status)