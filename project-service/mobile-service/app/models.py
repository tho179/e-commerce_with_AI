from django.db import models


class ElectronicsProduct(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    image_url = models.URLField(blank=True)
    price = models.DecimalField(max_digits=12, decimal_places=2)
    stock = models.IntegerField(default=0)
    brand = models.CharField(max_length=100, blank=True)
    model_code = models.CharField(max_length=100, blank=True)
    warranty_months = models.IntegerField(default=0)
    specs = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-id']

    def __str__(self):
        return self.name
