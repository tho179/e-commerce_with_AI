from django.core.management.base import BaseCommand
from app.models import FashionProduct


class Command(BaseCommand):
    help = 'Seed sample fashion products'

    def handle(self, *args, **options):
        seeds = [
            {
                'name': 'Ao Hoodie Unisex Basic',
                'description': 'Chat lieu ni mem, phu hop mua dong.',
                'price': '399000',
                'stock': 40,
                'size': 'M',
                'color': 'Den',
                'material': 'Cotton',
                'brand': 'UrbanViet',
                'image_url': 'https://images.unsplash.com/photo-1521572163474-6864f9cf17ab',
            },
            {
                'name': 'Quan Jean Slim Fit',
                'description': 'Form slim, de phoi cung ao so mi.',
                'price': '520000',
                'stock': 35,
                'size': 'L',
                'color': 'Xanh navy',
                'material': 'Denim',
                'brand': 'BlueDenim',
                'image_url': 'https://images.unsplash.com/photo-1542272604-787c3835535d',
            },
        ]

        created = 0
        for payload in seeds:
            _, was_created = FashionProduct.objects.get_or_create(name=payload['name'], defaults=payload)
            if was_created:
                created += 1

        self.stdout.write(self.style.SUCCESS(f'Seeded fashion products. Created: {created}'))
