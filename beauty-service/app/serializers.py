from rest_framework import serializers
from .models import BeautyProduct


class BeautyProductSerializer(serializers.ModelSerializer):
    category = serializers.SerializerMethodField()

    class Meta:
        model = BeautyProduct
        fields = [
            'id', 'name', 'description', 'image_url', 'price', 'stock',
            'brand', 'skin_type', 'concern', 'volume_ml', 'is_active', 'category'
        ]

    def get_category(self, obj):
        return 'lam_dep'
