from django.contrib import admin
from .models import FashionProduct


@admin.register(FashionProduct)
class FashionProductAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'price', 'size', 'color', 'stock')
    search_fields = ('name', 'color', 'material')
