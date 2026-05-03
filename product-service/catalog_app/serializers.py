from rest_framework import serializers

from .models import CatalogBook


class CatalogBookSerializer(serializers.ModelSerializer):
    class Meta:
        model = CatalogBook
        fields = '__all__'