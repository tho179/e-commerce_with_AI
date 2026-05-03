from django.contrib import admin
from .models import ElectronicsProduct


@admin.register(ElectronicsProduct)
class ElectronicsProductAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'price', 'warranty_months', 'stock')
    search_fields = ('name', 'brand', 'model_code')
