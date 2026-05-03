from django.urls import path

from .views import HealthCheck, ManagerListCreate

urlpatterns = [
    path('health/managers/', HealthCheck.as_view()),
    path('managers/', ManagerListCreate.as_view()),
]