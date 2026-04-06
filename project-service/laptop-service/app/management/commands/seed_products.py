from django.core.management.base import BaseCommand
from app.models import ElectronicsProduct


class Command(BaseCommand):
    help = 'Seed sample laptop products'

    def handle(self, *args, **options):
        seeds = [
            {
                'name': 'Laptop ProBook 14',
                'description': 'Laptop van phong gon nhe, pin ben.',
                'price': '18990000',
                'stock': 12,
                'brand': 'ProBook',
                'model_code': 'PB14-2026',
                'warranty_months': 24,
                'specs': {'ram': '16GB', 'storage': '512GB SSD', 'cpu': 'Intel i5'},
                'image_url': 'https://images.unsplash.com/photo-1496181133206-80ce9b88a853',
            },
            {
                'name': 'Laptop UltraBook Air 13',
                'description': 'Laptop mong nhe cho sinh vien va nhan vien van phong.',
                'price': '21990000',
                'stock': 16,
                'brand': 'UltraBook',
                'model_code': 'UBA13-2026',
                'warranty_months': 12,
                'specs': {'ram': '16GB', 'storage': '1TB SSD', 'cpu': 'Intel i7'},
                'image_url': 'https://images.unsplash.com/photo-1517336714739-489689fd1ca8',
            },
        ]

        created = 0
        for payload in seeds:
            _, was_created = ElectronicsProduct.objects.get_or_create(name=payload['name'], defaults=payload)
            if was_created:
                created += 1

        self.stdout.write(self.style.SUCCESS(f'Seeded laptop products. Created: {created}'))
