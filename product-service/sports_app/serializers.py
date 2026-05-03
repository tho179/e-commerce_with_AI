from rest_framework import serializers
from .models import SportsProduct


class SportsProductSerializer(serializers.ModelSerializer):
    category = serializers.SerializerMethodField()

    class Meta:
        model = SportsProduct
        fields = [
            'id', 'name', 'description', 'image_url', 'price', 'stock',
            'sport_type', 'size', 'material', 'fitness_level', 'brand', 'is_active', 'category'
        ]

    def get_category(self, obj):
        return 'the_thao'
