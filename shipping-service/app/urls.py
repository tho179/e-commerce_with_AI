from django.urls import path

from .views import HealthCheck, ShipmentCancel, ShipmentList, ShipmentReserve

urlpatterns = [
    path('health/', HealthCheck.as_view()),
    path('shipments/', ShipmentList.as_view()),
    path('shipments/reserve/', ShipmentReserve.as_view()),
    path('shipments/<int:shipment_id>/cancel/', ShipmentCancel.as_view()),
]