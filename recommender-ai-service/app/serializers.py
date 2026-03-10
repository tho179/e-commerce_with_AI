from rest_framework import serializers

from .models import RecommendationSnapshot


class RecommendationSnapshotSerializer(serializers.ModelSerializer):
    class Meta:
        model = RecommendationSnapshot
        fields = '__all__'