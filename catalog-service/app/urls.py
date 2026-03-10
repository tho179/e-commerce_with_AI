from django.urls import path

from .views import CatalogBookList, CatalogSync, HealthCheck

urlpatterns = [
    path('health/', HealthCheck.as_view()),
    path('catalog/books/', CatalogBookList.as_view()),
    path('catalog/sync/', CatalogSync.as_view()),
]