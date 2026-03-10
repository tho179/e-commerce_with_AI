from django.db import models


class CatalogBook(models.Model):
    external_book_id = models.IntegerField(unique=True)
    title = models.CharField(max_length=255)
    author = models.CharField(max_length=255)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.IntegerField()
    synced_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title