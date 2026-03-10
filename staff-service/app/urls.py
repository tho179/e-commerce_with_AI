from django.urls import path

from .views import HealthCheck, StaffListCreate

urlpatterns = [
    path('health/', HealthCheck.as_view()),
    path('staff/', StaffListCreate.as_view()),
]