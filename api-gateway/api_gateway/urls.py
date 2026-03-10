from django.urls import path

from .views import (
    add_cart_item,
    book_list,
    cart_lookup,
    create_customer,
    create_order,
    create_promotion,
    create_review,
    customer_list,
    delete_book,
    delete_cart_item,
    home,
    save_book,
    sync_catalog,
    update_book_price,
    update_cart_item,
    view_cart,
)

urlpatterns = [
    path('', home),
    path('staff/books/', book_list),
    path('staff/books/save/', save_book),
    path('staff/books/<int:book_id>/price/', update_book_price),
    path('staff/books/<int:book_id>/promotions/add/', create_promotion),
    path('staff/books/<int:book_id>/delete/', delete_book),
    path('staff/catalog/sync/', sync_catalog),
    path('customers/', customer_list),
    path('customers/create/', create_customer),
    path('customer/cart/', cart_lookup),
    path('customer/cart/<int:customer_id>/', view_cart),
    path('customer/cart/<int:customer_id>/items/add/', add_cart_item),
    path('customer/cart/<int:customer_id>/items/<int:item_id>/update/', update_cart_item),
    path('customer/cart/<int:customer_id>/items/<int:item_id>/delete/', delete_cart_item),
    path('customer/cart/<int:customer_id>/order/', create_order),
    path('customer/cart/<int:customer_id>/review/', create_review),
]