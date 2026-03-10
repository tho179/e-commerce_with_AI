from django.db import models


class Order(models.Model):
    customer_id = models.IntegerField()
    cart_id = models.IntegerField()
    status = models.CharField(max_length=20, default="pending")
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    payment_method = models.CharField(max_length=50)
    shipping_method = models.CharField(max_length=50)
    shipping_address = models.TextField()
    payment_reference = models.CharField(max_length=50, blank=True)
    shipment_reference = models.CharField(max_length=50, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Order #{self.id}"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    book_id = models.IntegerField()
    quantity = models.IntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"OrderItem #{self.id}"