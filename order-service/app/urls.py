from django.urls import path

from .views import HealthCheck, OrderListCreate, PurchasedBookDetailView, PurchasedBooksView

urlpatterns = [
    path('health/', HealthCheck.as_view()),
    path('orders/', OrderListCreate.as_view()),
    path('customers/<int:customer_id>/purchased-books/', PurchasedBooksView.as_view()),
    path('customers/<int:customer_id>/purchased-books/<int:book_id>/', PurchasedBookDetailView.as_view()),
]