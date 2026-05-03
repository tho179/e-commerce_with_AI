from django.core.management.base import BaseCommand
from sports_app.models import SportsProduct


class Command(BaseCommand):
    help = 'Seed sample sports products'

    def handle(self, *args, **options):
        seeds = [
            {
                'name': 'Thảm tập Yoga FlexPro 6mm',
                'description': 'Độ bám tốt, chống trượt, dễ vệ sinh sau khi tập.',
                'price': '450000',
                'stock': 44,
                'sport_type': 'yoga',
                'size': '183x61cm',
                'material': 'TPE',
                'fitness_level': 'beginner',
                'brand': 'FlexPro',
                'image_url': 'https://images.unsplash.com/photo-1518611012118-696072aa579a',
            },
            {
                'name': 'Tạ đơn PowerLift 12kg',
                'description': 'Tạ bọc cao su đặc, phù hợp tập sức mạnh tại nhà.',
                'price': '690000',
                'stock': 26,
                'sport_type': 'fitness',
                'size': '12kg',
                'material': 'rubber_iron',
                'fitness_level': 'intermediate',
                'brand': 'PowerLift',
                'image_url': 'https://images.unsplash.com/photo-1534367610401-9f5ed68180aa',
            },
            {
                'name': 'Giày chạy bộ AirRun X',
                'description': 'Đệm khí êm, trọng lượng nhẹ, hỗ trợ chạy bộ quãng dài.',
                'price': '1250000',
                'stock': 38,
                'sport_type': 'running',
                'size': '42',
                'material': 'mesh',
                'fitness_level': 'all',
                'brand': 'AirRun',
                'image_url': 'https://images.unsplash.com/photo-1542291026-7eec264c27ff',
            },
        ]

        valid_names = {payload['name'] for payload in seeds}
        SportsProduct.objects.exclude(name__in=valid_names).delete()

        created = 0
        for payload in seeds:
            _, was_created = SportsProduct.objects.update_or_create(name=payload['name'], defaults=payload)
            if was_created:
                created += 1

        self.stdout.write(self.style.SUCCESS(f'Seeded sports products. Created: {created}'))
