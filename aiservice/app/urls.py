from django.urls import path

from .views import (
    ChatAdviceView,
    DriftStatusView,
    GraphRAGChatView,
    HealthCheck,
    RecommendationView,
    RetrainTriggerView,
    ReviewInsights,
    ReviewListCreate,
    ReviewModelStatus,
    SemanticSearchView,
)

urlpatterns = [
    path('health/', HealthCheck.as_view()),
    path('search/semantic/', SemanticSearchView.as_view()),
    path('recommendations/<int:customer_id>/', RecommendationView.as_view()),
    path('ai/drift/', DriftStatusView.as_view()),
    path('ai/retrain/', RetrainTriggerView.as_view()),
    path('reviews/', ReviewListCreate.as_view()),
    path('reviews/insights/', ReviewInsights.as_view()),
    path('reviews/model-status/', ReviewModelStatus.as_view()),
    path('chat/advice/', ChatAdviceView.as_view()),
    path('chat/rag/graph/', GraphRAGChatView.as_view()),
]
