from django.http import JsonResponse
from rest_framework import viewsets
from rest_framework.decorators import api_view
from .models import SportsProduct
from .serializers import SportsProductSerializer


class SportsProductViewSet(viewsets.ModelViewSet):
    queryset = SportsProduct.objects.all()
    serializer_class = SportsProductSerializer


@api_view(['GET'])
def health(request):
    return JsonResponse({'status': 'ok', 'service': 'product-service/sports'})
