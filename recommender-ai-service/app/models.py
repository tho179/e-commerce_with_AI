from django.db import models


class RecommendationSnapshot(models.Model):
    customer_id = models.IntegerField()
    recommendations = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"RecommendationSnapshot #{self.id}"