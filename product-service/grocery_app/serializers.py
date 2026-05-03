from rest_framework import serializers
from .models import GroceryProduct


class GroceryProductSerializer(serializers.ModelSerializer):
    category = serializers.SerializerMethodField()

    class Meta:
        model = GroceryProduct
        fields = [
            'id', 'name', 'description', 'image_url', 'price', 'stock',
            'brand', 'unit', 'expiry_days', 'origin_country', 'organic', 'is_active', 'category'
        ]

    def get_category(self, obj):
        return 'tieu_dung'
