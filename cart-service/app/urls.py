from django.urls import path
from .views import AddCartItem, CartCreate, CartItemDetail, HealthCheck, ViewCart

urlpatterns = [
    path('health/', HealthCheck.as_view()),
    path('carts/', CartCreate.as_view()),
    path('cart-items/', AddCartItem.as_view()), # Đường dẫn khớp với localhost:8003/cart-items/
    path('cart-items/<int:item_id>/', CartItemDetail.as_view()),
    path('carts/<int:customer_id>/', ViewCart.as_view()),
]