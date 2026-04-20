from django.core.management.base import BaseCommand
from app.models import ElectronicsProduct


class Command(BaseCommand):
    help = 'Seed sản phẩm điện thoại mẫu'

    def handle(self, *args, **options):
        seeds = [
            {
                'name': 'Điện thoại Nova X 5G',
                'description': 'Màn hình 6.7 inch, camera 50MP, pin 5000mAh.',
                'price': '12990000',
                'stock': 20,
                'brand': 'NovaTech',
                'model_code': 'NVX5G-2026',
                'warranty_months': 18,
                'specs': {'ram': '12GB', 'storage': '256GB', 'chip': 'Snapdragon'},
                'image_url': 'https://images.unsplash.com/photo-1511707171634-5f897ff02aa9',
            },
            {
                'name': 'Điện thoại AirPhone S',
                'description': 'Thiết kế mỏng nhẹ, màn hình OLED 120Hz, sạc nhanh 65W.',
                'price': '15990000',
                'stock': 14,
                'brand': 'AirPhone',
                'model_code': 'APS-2026',
                'warranty_months': 18,
                'specs': {'ram': '12GB', 'storage': '512GB', 'camera': '108MP'},
                'image_url': 'https://images.unsplash.com/photo-1598327105666-5b89351aff97',
            },
        ]

        valid_names = {payload['name'] for payload in seeds}
        ElectronicsProduct.objects.exclude(name__in=valid_names).delete()

        created = 0
        for payload in seeds:
            _, was_created = ElectronicsProduct.objects.update_or_create(name=payload['name'], defaults=payload)
            if was_created:
                created += 1

        self.stdout.write(self.style.SUCCESS(f'Seeded electronics products. Created: {created}'))
