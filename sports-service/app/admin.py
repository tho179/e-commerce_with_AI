from django.contrib import admin
from .models import SportsProduct


@admin.register(SportsProduct)
class SportsProductAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'price', 'sport_type', 'fitness_level', 'stock')
    search_fields = ('name', 'sport_type', 'brand', 'material')
