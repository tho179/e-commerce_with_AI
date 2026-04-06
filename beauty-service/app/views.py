from django.http import JsonResponse
from rest_framework import viewsets
from rest_framework.decorators import api_view
from .models import BeautyProduct
from .serializers import BeautyProductSerializer


class BeautyProductViewSet(viewsets.ModelViewSet):
    queryset = BeautyProduct.objects.all()
    serializer_class = BeautyProductSerializer


@api_view(['GET'])
def health(request):
    return JsonResponse({'status': 'ok', 'service': 'beauty-service'})
