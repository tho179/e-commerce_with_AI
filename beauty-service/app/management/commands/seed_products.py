from django.core.management.base import BaseCommand
from app.models import BeautyProduct


class Command(BaseCommand):
    help = 'Seed sample beauty products'

    def handle(self, *args, **options):
        seeds = [
            {
                'name': 'Serum Niacinamide 10% GlowLab',
                'description': 'Ho tro giam tham mun va kiem soat dau cho da hon hop.',
                'price': '289000',
                'stock': 55,
                'brand': 'GlowLab',
                'skin_type': 'da_hon_hop',
                'concern': 'tham_mun',
                'volume_ml': 30,
                'image_url': 'https://images.unsplash.com/photo-1571781926291-c477ebfd024b',
            },
            {
                'name': 'Kem Chong Nang UV Shield SPF50+',
                'description': 'Ket cau nhe, khong nang mat, phu hop su dung hang ngay.',
                'price': '349000',
                'stock': 48,
                'brand': 'SunDerma',
                'skin_type': 'da_nhay_cam',
                'concern': 'chong_nang',
                'volume_ml': 50,
                'image_url': 'https://images.unsplash.com/photo-1556228720-195a672e8a03',
            },
            {
                'name': 'Sua Rua Mat Amino Fresh Clean',
                'description': 'Lam sach diu nhe, giu do am tu nhien cho da.',
                'price': '215000',
                'stock': 62,
                'brand': 'DermaFresh',
                'skin_type': 'da_kho',
                'concern': 'lam_sach',
                'volume_ml': 120,
                'image_url': 'https://images.unsplash.com/photo-1570172619644-dfd03ed5d881',
            },
        ]

        created = 0
        for payload in seeds:
            _, was_created = BeautyProduct.objects.get_or_create(name=payload['name'], defaults=payload)
            if was_created:
                created += 1

        self.stdout.write(self.style.SUCCESS(f'Seeded beauty products. Created: {created}'))
