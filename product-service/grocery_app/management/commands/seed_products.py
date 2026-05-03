from django.core.management.base import BaseCommand
from grocery_app.models import GroceryProduct


class Command(BaseCommand):
    help = 'Seed sample grocery products'

    def handle(self, *args, **options):
        seeds = [
            {
                'name': 'Yến mạch nguyên hạt OatPlus 1kg',
                'description': 'Yến mạch ăn sáng giàu chất xơ, phù hợp chế độ dinh dưỡng lành mạnh.',
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
                'name': 'Sữa tươi tiệt trùng FarmFresh 1L',
                'description': 'Sữa tươi bổ sung canxi, phù hợp cho cả gia đình.',
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
                'name': 'Nước rửa chén BioClean 750ml',
                'description': 'Làm sạch nhanh, mùi hương dịu nhẹ, an toàn cho da tay.',
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

        valid_names = {payload['name'] for payload in seeds}
        GroceryProduct.objects.exclude(name__in=valid_names).delete()

        created = 0
        for payload in seeds:
            _, was_created = GroceryProduct.objects.update_or_create(name=payload['name'], defaults=payload)
            if was_created:
                created += 1

        self.stdout.write(self.style.SUCCESS(f'Seeded grocery products. Created: {created}'))
