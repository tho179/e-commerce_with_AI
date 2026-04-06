from django.db import models


class Review(models.Model):
    customer_id = models.IntegerField()
    book_id = models.IntegerField()
    rating = models.IntegerField()
    comment = models.TextField(blank=True)
    sentiment_label = models.CharField(max_length=16, default="neutral")
    sentiment_score = models.FloatField(default=0.5)
    aspect_tags = models.JSONField(default=list, blank=True)
    advice = models.TextField(blank=True)
    ai_metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Review #{self.id}"