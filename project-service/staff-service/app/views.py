from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Staff
from .serializers import StaffSerializer


class HealthCheck(APIView):
    def get(self, request):
        return Response({"service": "staff-service", "status": "ok"})


class StaffListCreate(APIView):
    def get(self, request):
        serializer = StaffSerializer(Staff.objects.all(), many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = StaffSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=400)