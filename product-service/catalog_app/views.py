import requests
from rest_framework.response import Response
from rest_framework.views import APIView
import os

from .models import CatalogBook
from .serializers import CatalogBookSerializer
from django.db import models

BOOK_SERVICE_URL = "http://product-service:8000"
SERVICE_SHARED_TOKEN = os.getenv("SERVICE_SHARED_TOKEN", "")


def _internal_headers():
    if not SERVICE_SHARED_TOKEN:
        return {}
    return {"X-Service-Token": SERVICE_SHARED_TOKEN}


class HealthCheck(APIView):
    def get(self, request):
        return Response({"service": "product-service/catalog", "status": "ok"})


class CatalogBookList(APIView):
    def get(self, request):
        serializer = CatalogBookSerializer(CatalogBook.objects.all(), many=True)
        return Response(serializer.data)


class CatalogSync(APIView):
    def post(self, request):
        try:
            response = requests.get(f"{BOOK_SERVICE_URL}/books/", timeout=5, headers=_internal_headers())
            response.raise_for_status()
        except requests.RequestException:
            return Response({"error": "Book service unavailable"}, status=503)

        synced = []
        for book in response.json():
            catalog_book, _ = CatalogBook.objects.update_or_create(
                external_book_id=book["id"],
                defaults={
                    "title": book["title"],
                    "author": book["author"],
                    "category": book.get("category", "sach"),
                    "description": book.get("description", ""),
                    "image_url": book.get("image_url", ""),
                    "price": book["price"],
                    "stock": book["stock"],
                },
            )
            synced.append(catalog_book)

        serializer = CatalogBookSerializer(synced, many=True)
        return Response(serializer.data)
    