from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Book, Promotion
from .serializers import BookSerializer, PromotionSerializer


class HealthCheck(APIView):
    def get(self, request):
        return Response({"service": "book-service", "status": "ok"})

class BookListCreate(APIView):
    def get(self, request):
        books = Book.objects.all()
        serializer = BookSerializer(books, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = BookSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=400)


class BookDetail(APIView):
    def get(self, request, book_id):
        try:
            book = Book.objects.get(id=book_id)
        except Book.DoesNotExist:
            return Response({"error": "San pham khong ton tai"}, status=404)

        serializer = BookSerializer(book)
        return Response(serializer.data)

    def put(self, request, book_id):
        try:
            book = Book.objects.get(id=book_id)
        except Book.DoesNotExist:
            return Response({"error": "San pham khong ton tai"}, status=404)

        serializer = BookSerializer(book, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=400)

    def delete(self, request, book_id):
        try:
            book = Book.objects.get(id=book_id)
        except Book.DoesNotExist:
            return Response({"error": "San pham khong ton tai"}, status=404)

        book.delete()
        return Response(status=204)


class BookPriceUpdate(APIView):
    def put(self, request, book_id):
        try:
            book = Book.objects.get(id=book_id)
        except Book.DoesNotExist:
            return Response({"error": "San pham khong ton tai"}, status=404)

        price = request.data.get("price")
        serializer = BookSerializer(book, data={"price": price}, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=400)


class PromotionListCreate(APIView):
    def get(self, request):
        promotions = Promotion.objects.select_related("book").all().order_by("-created_at")
        serializer = PromotionSerializer(promotions, many=True)
        return Response(serializer.data)

    def post(self, request):
        book_id = request.data.get("book")
        if not Book.objects.filter(id=book_id).exists():
            return Response({"error": "San pham khong ton tai"}, status=404)

        Promotion.objects.filter(book_id=book_id, is_active=True).update(is_active=False)
        serializer = PromotionSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(is_active=True)
            return Response(serializer.data, status=201)
        return Response(serializer.errors, status=400)