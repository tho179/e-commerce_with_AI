from django.http import JsonResponse
from rest_framework import viewsets
from rest_framework.decorators import api_view
from .models import ElectronicsProduct
from .serializers import ElectronicsProductSerializer


class ElectronicsProductViewSet(viewsets.ModelViewSet):
    queryset = ElectronicsProduct.objects.all()
    serializer_class = ElectronicsProductSerializer


@api_view(['GET'])
def health(request):
    return JsonResponse({'status': 'ok', 'service': 'mobile-service'})
