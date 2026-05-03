from rest_framework import serializers
from .models import HouseholdProduct


class HouseholdProductSerializer(serializers.ModelSerializer):
    category = serializers.SerializerMethodField()

    class Meta:
        model = HouseholdProduct
        fields = [
            'id', 'name', 'description', 'image_url', 'price', 'stock',
            'usage_area', 'expiry_days', 'unit', 'brand', 'is_active', 'category'
        ]

    def get_category(self, obj):
        return 'household'
