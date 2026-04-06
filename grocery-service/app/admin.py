from django.contrib import admin
from .models import GroceryProduct


@admin.register(GroceryProduct)
class GroceryProductAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'price', 'unit', 'expiry_days', 'stock')
    search_fields = ('name', 'brand', 'origin_country')
