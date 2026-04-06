from django.http import JsonResponse
from rest_framework import viewsets
from rest_framework.decorators import api_view
from .models import GroceryProduct
from .serializers import GroceryProductSerializer


class GroceryProductViewSet(viewsets.ModelViewSet):
    queryset = GroceryProduct.objects.all()
    serializer_class = GroceryProductSerializer


@api_view(['GET'])
def health(request):
    return JsonResponse({'status': 'ok', 'service': 'grocery-service'})
