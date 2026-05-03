from django.urls import include, path
from rest_framework.routers import DefaultRouter
from .views import GroceryProductViewSet, health


router = DefaultRouter()
router.register(r'products', GroceryProductViewSet, basename='grocery-product')

urlpatterns = [
    path('', include(router.urls)),
    path('health/', health, name='health'),
]
