from django.db import models


class Shipment(models.Model):
    order_id = models.IntegerField()
    customer_id = models.IntegerField()
    address = models.TextField()
    method = models.CharField(max_length=50)
    status = models.CharField(max_length=20, default="reserved")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Shipment #{self.id}"