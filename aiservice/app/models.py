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


class RecommendationSnapshot(models.Model):
	customer_id = models.IntegerField()
	recommendations = models.JSONField(default=list)
	created_at = models.DateTimeField(auto_now_add=True)

	def __str__(self):
		return f"RecommendationSnapshot #{self.id}"


class ModelDriftSnapshot(models.Model):
	source = models.CharField(max_length=40, default="system")
	review_count = models.IntegerField(default=0)
	average_rating = models.FloatField(default=0.0)
	average_sentiment = models.FloatField(default=0.0)
	divergence = models.FloatField(default=0.0)
	negative_ratio = models.FloatField(default=0.0)
	needs_retrain = models.BooleanField(default=False)
	note = models.TextField(blank=True)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ["-id"]

	def __str__(self):
		return f"ModelDriftSnapshot #{self.id} ({self.source})"
