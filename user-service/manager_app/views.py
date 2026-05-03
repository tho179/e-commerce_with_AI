from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Manager
from .serializers import ManagerSerializer


class HealthCheck(APIView):
    def get(self, request):
        return Response({"service": "user-service/managers", "status": "ok"})


class ManagerListCreate(APIView):
    def get(self, request):
        serializer = ManagerSerializer(Manager.objects.all(), many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = ManagerSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=400)