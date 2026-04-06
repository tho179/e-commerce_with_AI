from django.urls import path

from .views import HealthCheck, ReviewInsights, ReviewListCreate, ReviewModelStatus

urlpatterns = [
    path('health/', HealthCheck.as_view()),
    path('reviews/', ReviewListCreate.as_view()),
    path('reviews/insights/', ReviewInsights.as_view()),
    path('reviews/model-status/', ReviewModelStatus.as_view()),
]