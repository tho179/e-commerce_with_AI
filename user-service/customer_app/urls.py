from django.urls import path

from .views import CustomerListCreate, HealthCheck

urlpatterns = [
    path('health/customers/', HealthCheck.as_view()),
    path('customers/', CustomerListCreate.as_view()),
]
