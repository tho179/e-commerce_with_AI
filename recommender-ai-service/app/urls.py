from django.urls import path

from .views import DriftStatusView, HealthCheck, RecommendationView, RetrainTriggerView

urlpatterns = [
    path('health/', HealthCheck.as_view()),
    path('recommendations/<int:customer_id>/', RecommendationView.as_view()),
    path('ai/drift/', DriftStatusView.as_view()),
    path('ai/retrain/', RetrainTriggerView.as_view()),
]