from rest_framework import serializers
from .models import FashionProduct


class FashionProductSerializer(serializers.ModelSerializer):
    category = serializers.SerializerMethodField()

    class Meta:
        model = FashionProduct
        fields = [
            'id', 'name', 'description', 'image_url', 'price', 'stock',
            'size', 'color', 'material', 'brand', 'is_active', 'category'
        ]

    def get_category(self, obj):
        return 'fashion'
