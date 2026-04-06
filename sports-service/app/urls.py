from django.urls import include, path
from rest_framework.routers import DefaultRouter
from .views import SportsProductViewSet, health


router = DefaultRouter()
router.register(r'products', SportsProductViewSet, basename='sports-product')

urlpatterns = [
    path('', include(router.urls)),
    path('health/', health, name='health'),
]
