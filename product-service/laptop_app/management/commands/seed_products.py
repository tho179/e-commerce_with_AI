from django.core.management.base import BaseCommand
from laptop_app.models import ElectronicsProduct


class Command(BaseCommand):
    help = 'Seed sản phẩm laptop mẫu'

    def handle(self, *args, **options):
        seeds = [
            {
                'name': 'Laptop ProBook 14 inch',
                'description': 'Laptop văn phòng gọn nhẹ, pin bền, phù hợp học tập và làm việc.',
                'price': '18990000',
                'stock': 12,
                'brand': 'ProBook',
                'model_code': 'PB14-2026',
                'warranty_months': 24,
                'specs': {'ram': '16GB', 'storage': '512GB SSD', 'cpu': 'Intel i5'},
                'image_url': 'https://images.unsplash.com/photo-1496181133206-80ce9b88a853',
            },
            {
                'name': 'Laptop UltraBook Air 13 inch',
                'description': 'Laptop mỏng nhẹ cho sinh viên và nhân viên văn phòng.',
                'price': '21990000',
                'stock': 16,
                'brand': 'UltraBook',
                'model_code': 'UBA13-2026',
                'warranty_months': 12,
                'specs': {'ram': '16GB', 'storage': '1TB SSD', 'cpu': 'Intel i7'},
                'image_url': 'https://images.unsplash.com/photo-1517336714739-489689fd1ca8',
            },
        ]

        valid_names = {payload['name'] for payload in seeds}
        ElectronicsProduct.objects.exclude(name__in=valid_names).delete()

        created = 0
        for payload in seeds:
            _, was_created = ElectronicsProduct.objects.update_or_create(name=payload['name'], defaults=payload)
            if was_created:
                created += 1

        self.stdout.write(self.style.SUCCESS(f'Seeded laptop products. Created: {created}'))
