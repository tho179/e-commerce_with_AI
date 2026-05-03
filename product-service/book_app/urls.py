from django.urls import path

from .views import BookDetail, BookListCreate, BookPriceUpdate, HealthCheck, PromotionListCreate

urlpatterns = [
    path('health/books/', HealthCheck.as_view()),
    path('books/', BookListCreate.as_view()),
    path('books/<int:book_id>/', BookDetail.as_view()),
    path('books/<int:book_id>/price/', BookPriceUpdate.as_view()),
    path('promotions/', PromotionListCreate.as_view()),
]