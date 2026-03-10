from django.db import models

class Cart(models.Model):
    customer_id = models.IntegerField() # ID từ Customer Service [cite: 254]

class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE) # [cite: 256]
    book_id = models.IntegerField() # ID từ Book Service [cite: 257]
    quantity = models.IntegerField() # [cite: 259]