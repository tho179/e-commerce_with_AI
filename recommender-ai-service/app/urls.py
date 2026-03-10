from django.urls import path

from .views import HealthCheck, RecommendationView

urlpatterns = [
    path('health/', HealthCheck.as_view()),
    path('recommendations/<int:customer_id>/', RecommendationView.as_view()),
]