from django.core.management.base import BaseCommand
from app.models import ElectronicsProduct


class Command(BaseCommand):
    help = 'Seed sample electronics products'

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
                'name': 'Tai Nghe Bluetooth SoundAir X2',
                'description': 'Chong on co ban, ket noi on dinh Bluetooth 5.3.',
                'price': '1290000',
                'stock': 28,
                'brand': 'SoundAir',
                'model_code': 'SAX2',
                'warranty_months': 12,
                'specs': {'battery': '36h', 'bluetooth': '5.3'},
                'image_url': 'https://images.unsplash.com/photo-1546435770-a3e426bf472b',
            },
        ]

        created = 0
        for payload in seeds:
            _, was_created = ElectronicsProduct.objects.get_or_create(name=payload['name'], defaults=payload)
            if was_created:
                created += 1

        self.stdout.write(self.style.SUCCESS(f'Seeded electronics products. Created: {created}'))
