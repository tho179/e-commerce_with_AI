from decimal import Decimal

from rest_framework import serializers

from .models import Book, Promotion


class PromotionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Promotion
        fields = '__all__'

    def validate_discount_percent(self, value):
        if value <= 0 or value > 100:
            raise serializers.ValidationError("Discount percent must be between 1 and 100.")
        return value

class BookSerializer(serializers.ModelSerializer):
    active_promotion = serializers.SerializerMethodField()
    effective_price = serializers.SerializerMethodField()

    class Meta:
        model = Book
        fields = '__all__'

    def get_active_promotion(self, obj):
        promotion = obj.promotions.filter(is_active=True).order_by('-created_at').first()
        if not promotion:
            return None
        return PromotionSerializer(promotion).data

    def get_effective_price(self, obj):
        promotion = obj.promotions.filter(is_active=True).order_by('-created_at').first()
        price = Decimal(str(obj.price))
        if not promotion:
            return price
        discounted_price = price * Decimal(100 - promotion.discount_percent) / Decimal(100)
        return discounted_price.quantize(Decimal("0.01"))