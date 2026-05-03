from django.http import JsonResponse
from rest_framework import viewsets
from rest_framework.decorators import api_view
from .models import FashionProduct
from .serializers import FashionProductSerializer


class FashionProductViewSet(viewsets.ModelViewSet):
    queryset = FashionProduct.objects.all()
    serializer_class = FashionProductSerializer


@api_view(['GET'])
def health(request):
    return JsonResponse({'status': 'ok', 'service': 'product-service/fashion'})
