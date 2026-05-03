from django.contrib import admin
from .models import BeautyProduct


@admin.register(BeautyProduct)
class BeautyProductAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'price', 'skin_type', 'concern', 'stock')
    search_fields = ('name', 'brand', 'skin_type', 'concern')
