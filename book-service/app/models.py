from django.db import models


class Book(models.Model):
    CATEGORY_CHOICES = [
        ("sach", "Sách"),
    ]

    title = models.CharField(max_length=255)
    author = models.CharField(max_length=255)
    category = models.CharField(max_length=32, choices=CATEGORY_CHOICES, default="sach")
    description = models.TextField(blank=True, default="")
    image_url = models.URLField(blank=True, default="")
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.IntegerField()


class Promotion(models.Model):
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name="promotions")
    name = models.CharField(max_length=255)
    discount_percent = models.PositiveIntegerField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} - {self.book.title}"
    