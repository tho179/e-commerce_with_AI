from django.core.management.base import BaseCommand
from app.models import SportsProduct


class Command(BaseCommand):
    help = 'Seed sample sports products'

    def handle(self, *args, **options):
        seeds = [
            {
                'name': 'Yoga Mat FlexPro 6mm',
                'description': 'Tham tap do bam tot, chong truot, de ve sinh sau khi tap.',
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
                'name': 'Ta don PowerLift 12kg',
                'description': 'Ta don bo cao su dac, phu hop tap suc manh tai nha.',
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
                'name': 'Giay Chay Bo AirRun X',
                'description': 'Dem khi em, trong luong nhe, ho tro chay bo duong dai.',
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

        created = 0
        for payload in seeds:
            _, was_created = SportsProduct.objects.get_or_create(name=payload['name'], defaults=payload)
            if was_created:
                created += 1

        self.stdout.write(self.style.SUCCESS(f'Seeded sports products. Created: {created}'))
