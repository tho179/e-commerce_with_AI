from django.urls import include, path
from rest_framework.routers import DefaultRouter
from .views import LaptopProductViewSet, health


router = DefaultRouter()
router.register(r'products', LaptopProductViewSet, basename='laptop-product')

urlpatterns = [
    path('', include(router.urls)),
    path('health/', health, name='health'),
]
