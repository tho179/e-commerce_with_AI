from django.urls import path

from .views import HealthCheck, ReviewListCreate

urlpatterns = [
    path('health/', HealthCheck.as_view()),
    path('reviews/', ReviewListCreate.as_view()),
]