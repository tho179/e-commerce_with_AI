from django.urls import include, path
from rest_framework.routers import DefaultRouter
from .views import ElectronicsProductViewSet, health


router = DefaultRouter()
router.register(r'products', ElectronicsProductViewSet, basename='mobile-product')

urlpatterns = [
    path('', include(router.urls)),
    path('health/', health, name='health'),
]
