from django.core.management.base import BaseCommand
from household_app.models import HouseholdProduct


class Command(BaseCommand):
    help = 'Seed sample household products'

    def handle(self, *args, **options):
        seeds = [
            {
                'name': 'Nồi chiên không dầu AirChef 5L',
                'description': 'Công nghệ đối lưu nhiệt, giảm dầu mỡ, dễ vệ sinh sau khi nấu.',
                'price': '1490000',
                'stock': 22,
                'usage_area': 'Nhà bếp',
                'expiry_days': 0,
                'unit': 'cai',
                'brand': 'AirChef',
                'image_url': 'https://images.unsplash.com/photo-1585515656240-2f8a6fbbf468',
            },
            {
                'name': 'Nước lau sàn FreshHome 3L',
                'description': 'Mùi hương dịu nhẹ, làm sạch nhanh và ít bám trơn trượt.',
                'price': '119000',
                'stock': 50,
                'usage_area': 'Phòng khách',
                'expiry_days': 730,
                'unit': 'chai',
                'brand': 'FreshHome',
                'image_url': 'https://images.unsplash.com/photo-1581578731548-c64695cc6952',
            },
        ]

        valid_names = {payload['name'] for payload in seeds}
        HouseholdProduct.objects.exclude(name__in=valid_names).delete()

        created = 0
        for payload in seeds:
            _, was_created = HouseholdProduct.objects.update_or_create(name=payload['name'], defaults=payload)
            if was_created:
                created += 1

        self.stdout.write(self.style.SUCCESS(f'Seeded household products. Created: {created}'))
