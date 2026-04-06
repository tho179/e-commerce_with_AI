from django.core.management.base import BaseCommand
from app.models import GroceryProduct


class Command(BaseCommand):
    help = 'Seed sample grocery products'

    def handle(self, *args, **options):
        seeds = [
            {
                'name': 'Yen mach nguyen hat OatPlus 1kg',
                'description': 'Yen mach an sang, giau chat xo, hop dung cho che do healthy.',
                'price': '129000',
                'stock': 120,
                'brand': 'OatPlus',
                'unit': 'goi',
                'expiry_days': 365,
                'origin_country': 'Australia',
                'organic': True,
                'image_url': 'https://images.unsplash.com/photo-1515543904379-3d757afe72e2',
            },
            {
                'name': 'Sua tuoi tiệt trung FarmFresh 1L',
                'description': 'Sua tuoi bo sung canxi, phu hop cho ca gia dinh.',
                'price': '39000',
                'stock': 180,
                'brand': 'FarmFresh',
                'unit': 'hop',
                'expiry_days': 120,
                'origin_country': 'Viet Nam',
                'organic': False,
                'image_url': 'https://images.unsplash.com/photo-1550583724-b2692b85b150',
            },
            {
                'name': 'Nuoc rua chen BioClean 750ml',
                'description': 'Lam sach nhanh, mui huong diu nhe, an toan cho da tay.',
                'price': '55000',
                'stock': 95,
                'brand': 'BioClean',
                'unit': 'chai',
                'expiry_days': 540,
                'origin_country': 'Thai Lan',
                'organic': False,
                'image_url': 'https://images.unsplash.com/photo-1583947582886-f40ec95dd752',
            },
        ]

        created = 0
        for payload in seeds:
            _, was_created = GroceryProduct.objects.get_or_create(name=payload['name'], defaults=payload)
            if was_created:
                created += 1

        self.stdout.write(self.style.SUCCESS(f'Seeded grocery products. Created: {created}'))
