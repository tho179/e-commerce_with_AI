from rest_framework import serializers

from .models import ModelDriftSnapshot, RecommendationSnapshot


class RecommendationSnapshotSerializer(serializers.ModelSerializer):
    class Meta:
        model = RecommendationSnapshot
        fields = '__all__'


class ModelDriftSnapshotSerializer(serializers.ModelSerializer):
    class Meta:
        model = ModelDriftSnapshot
        fields = '__all__'