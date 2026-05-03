from django.urls import path

from .views import HealthCheck, StaffListCreate

urlpatterns = [
    path('health/staff/', HealthCheck.as_view()),
    path('staff/', StaffListCreate.as_view()),
]