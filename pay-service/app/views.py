from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Payment
from .serializers import PaymentSerializer


class HealthCheck(APIView):
    def get(self, request):
        return Response({"service": "pay-service", "status": "ok"})


class PaymentList(APIView):
    def get(self, request):
        serializer = PaymentSerializer(Payment.objects.all(), many=True)
        return Response(serializer.data)


class PaymentReserve(APIView):
    def post(self, request):
        serializer = PaymentSerializer(data=request.data)
        if serializer.is_valid():
            payment = serializer.save(status="reserved")
            return Response(PaymentSerializer(payment).data)
        return Response(serializer.errors, status=400)


class PaymentCancel(APIView):
    def post(self, request, payment_id):
        try:
            payment = Payment.objects.get(id=payment_id)
        except Payment.DoesNotExist:
            return Response({"error": "Payment not found"}, status=404)

        payment.status = "cancelled"
        payment.save(update_fields=["status"])
        return Response(PaymentSerializer(payment).data)