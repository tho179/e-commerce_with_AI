from django.http import JsonResponse
from rest_framework import viewsets
from rest_framework.decorators import api_view
from .models import HouseholdProduct
from .serializers import HouseholdProductSerializer


class HouseholdProductViewSet(viewsets.ModelViewSet):
    queryset = HouseholdProduct.objects.all()
    serializer_class = HouseholdProductSerializer


@api_view(['GET'])
def health(request):
    return JsonResponse({'status': 'ok', 'service': 'product-service/household'})
