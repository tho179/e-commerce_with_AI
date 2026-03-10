from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Shipment
from .serializers import ShipmentSerializer


class HealthCheck(APIView):
    def get(self, request):
        return Response({"service": "ship-service", "status": "ok"})


class ShipmentList(APIView):
    def get(self, request):
        serializer = ShipmentSerializer(Shipment.objects.all(), many=True)
        return Response(serializer.data)


class ShipmentReserve(APIView):
    def post(self, request):
        serializer = ShipmentSerializer(data=request.data)
        if serializer.is_valid():
            shipment = serializer.save(status="reserved")
            return Response(ShipmentSerializer(shipment).data)
        return Response(serializer.errors, status=400)


class ShipmentCancel(APIView):
    def post(self, request, shipment_id):
        try:
            shipment = Shipment.objects.get(id=shipment_id)
        except Shipment.DoesNotExist:
            return Response({"error": "Shipment not found"}, status=404)

        shipment.status = "cancelled"
        shipment.save(update_fields=["status"])
        return Response(ShipmentSerializer(shipment).data)