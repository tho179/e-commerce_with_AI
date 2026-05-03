from django.core.management.base import BaseCommand
from fashion_app.models import FashionProduct


class Command(BaseCommand):
    help = 'Seed sample fashion products'

    def handle(self, *args, **options):
        seeds = [
            {
                'name': 'Áo Hoodie Unisex Basic',
                'description': 'Chất liệu nỉ mềm, phù hợp mặc hằng ngày và mùa lạnh.',
                'price': '399000',
                'stock': 40,
                'size': 'M',
                'color': 'Đen',
                'material': 'Cotton',
                'brand': 'UrbanViet',
                'image_url': 'https://images.unsplash.com/photo-1521572163474-6864f9cf17ab',
            },
            {
                'name': 'Quần Jean Slim Fit',
                'description': 'Form slim dễ phối cùng áo sơ mi hoặc áo thun.',
                'price': '520000',
                'stock': 35,
                'size': 'L',
                'color': 'Xanh navy',
                'material': 'Denim',
                'brand': 'BlueDenim',
                'image_url': 'https://images.unsplash.com/photo-1542272604-787c3835535d',
            },
        ]

        valid_names = {payload['name'] for payload in seeds}
        FashionProduct.objects.exclude(name__in=valid_names).delete()

        created = 0
        for payload in seeds:
            _, was_created = FashionProduct.objects.update_or_create(name=payload['name'], defaults=payload)
            if was_created:
                created += 1

        self.stdout.write(self.style.SUCCESS(f'Seeded fashion products. Created: {created}'))
