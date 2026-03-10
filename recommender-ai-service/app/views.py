from collections import defaultdict

import requests
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import RecommendationSnapshot
from .serializers import RecommendationSnapshotSerializer

BOOK_SERVICE_URL = "http://book-service:8000"
REVIEW_SERVICE_URL = "http://comment-rate-service:8000"


class HealthCheck(APIView):
    def get(self, request):
        return Response({"service": "recommender-ai-service", "status": "ok"})


class RecommendationView(APIView):
    def get(self, request, customer_id):
        try:
            books_response = requests.get(f"{BOOK_SERVICE_URL}/books/", timeout=5)
            reviews_response = requests.get(f"{REVIEW_SERVICE_URL}/reviews/", timeout=5)
            books_response.raise_for_status()
            reviews_response.raise_for_status()
        except requests.RequestException:
            return Response({"error": "Dependency unavailable"}, status=503)

        books = books_response.json()
        reviews = reviews_response.json()
        scores = defaultdict(list)
        reviewed_by_customer = set()

        for review in reviews:
            scores[review["book_id"]].append(review["rating"])
            if review["customer_id"] == customer_id:
                reviewed_by_customer.add(review["book_id"])

        ranked_books = []
        for book in books:
            if book["id"] in reviewed_by_customer:
                continue
            ratings = scores.get(book["id"], [])
            average = sum(ratings) / len(ratings) if ratings else 0
            ranked_books.append({
                "book_id": book["id"],
                "title": book["title"],
                "score": average,
            })

        ranked_books.sort(key=lambda item: item["score"], reverse=True)
        recommendations = ranked_books[:5]
        snapshot = RecommendationSnapshot.objects.create(
            customer_id=customer_id,
            recommendations=recommendations,
        )
        serializer = RecommendationSnapshotSerializer(snapshot)
        return Response(serializer.data)