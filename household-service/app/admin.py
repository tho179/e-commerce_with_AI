from django.contrib import admin
from .models import HouseholdProduct


@admin.register(HouseholdProduct)
class HouseholdProductAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'price', 'usage_area', 'stock')
    search_fields = ('name', 'usage_area', 'brand')
