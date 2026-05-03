from django.db import models


class SportsProduct(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    image_url = models.URLField(blank=True)
    price = models.DecimalField(max_digits=12, decimal_places=2)
    stock = models.IntegerField(default=0)
    sport_type = models.CharField(max_length=50, blank=True)
    size = models.CharField(max_length=30, blank=True)
    material = models.CharField(max_length=100, blank=True)
    fitness_level = models.CharField(max_length=40, blank=True)
    brand = models.CharField(max_length=100, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-id']

    def __str__(self):
        return self.name
