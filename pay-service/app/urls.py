from django.urls import path

from .views import HealthCheck, PaymentCancel, PaymentList, PaymentReserve

urlpatterns = [
    path('health/', HealthCheck.as_view()),
    path('payments/', PaymentList.as_view()),
    path('payments/reserve/', PaymentReserve.as_view()),
    path('payments/<int:payment_id>/cancel/', PaymentCancel.as_view()),
]