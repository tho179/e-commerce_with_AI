from django.urls import path

from .views import HealthCheck, SemanticSearchView

urlpatterns = [
    path('health/', HealthCheck.as_view()),
    path('search/semantic/', SemanticSearchView.as_view()),
]
