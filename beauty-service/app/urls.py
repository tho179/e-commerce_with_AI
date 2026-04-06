from django.urls import include, path
from rest_framework.routers import DefaultRouter
from .views import BeautyProductViewSet, health


router = DefaultRouter()
router.register(r'products', BeautyProductViewSet, basename='beauty-product')

urlpatterns = [
    path('', include(router.urls)),
    path('health/', health, name='health'),
]
