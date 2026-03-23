from django.core.management.base import BaseCommand
from app.models import HouseholdProduct


class Command(BaseCommand):
    help = 'Seed sample household products'

    def handle(self, *args, **options):
        seeds = [
            {
                'name': 'Noi Chien Khong Dau AirChef 5L',
                'description': 'Cong nghe doi luu nhiet, tiet kiem dau mo.',
                'price': '1490000',
                'stock': 22,
                'usage_area': 'Nha bep',
                'expiry_days': 0,
                'unit': 'cai',
                'brand': 'AirChef',
                'image_url': 'https://images.unsplash.com/photo-1570222094114-d054a817e56b',
            },
            {
                'name': 'Nuoc Lau San FreshHome 3L',
                'description': 'Mui huong de chiu, sach nhanh bong dep.',
                'price': '119000',
                'stock': 50,
                'usage_area': 'Phong khach',
                'expiry_days': 730,
                'unit': 'chai',
                'brand': 'FreshHome',
                'image_url': 'https://images.unsplash.com/photo-1581578731548-c64695cc6952',
            },
        ]

        created = 0
        for payload in seeds:
            _, was_created = HouseholdProduct.objects.get_or_create(name=payload['name'], defaults=payload)
            if was_created:
                created += 1

        self.stdout.write(self.style.SUCCESS(f'Seeded household products. Created: {created}'))
