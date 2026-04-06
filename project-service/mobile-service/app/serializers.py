from rest_framework import serializers
from .models import ElectronicsProduct


class ElectronicsProductSerializer(serializers.ModelSerializer):
    category = serializers.SerializerMethodField()

    class Meta:
        model = ElectronicsProduct
        fields = [
            'id', 'name', 'description', 'image_url', 'price', 'stock',
            'brand', 'model_code', 'warranty_months', 'specs', 'is_active', 'category'
        ]

    def get_category(self, obj):
        return 'mobile'
