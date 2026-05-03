from rest_framework.views import APIView
from rest_framework.response import Response
from .models import Customer
from .serializers import CustomerSerializer
import os
import requests

CART_SERVICE_URL = "http://cart-service:8000"
SERVICE_SHARED_TOKEN = os.getenv("SERVICE_SHARED_TOKEN", "")


def _internal_headers():
    if not SERVICE_SHARED_TOKEN:
        return {}
    return {"X-Service-Token": SERVICE_SHARED_TOKEN}


class HealthCheck(APIView):
    def get(self, request):
        return Response({"service": "user-service/customers", "status": "ok"})

class CustomerListCreate(APIView):
    def get(self, request):
        customers = Customer.objects.all()
        serializer = CustomerSerializer(customers, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = CustomerSerializer(data=request.data)
        if serializer.is_valid():
            customer = serializer.save()
            # Tự động tạo giỏ hàng bên Cart Service [cite: 82]
            requests.post(
                f"{CART_SERVICE_URL}/carts/",
                json={"customer_id": customer.id},
                headers=_internal_headers(),
            )
            return Response(serializer.data)
        return Response(serializer.errors, status=400)