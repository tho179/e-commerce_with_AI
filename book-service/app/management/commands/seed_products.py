from decimal import Decimal

from django.core.management.base import BaseCommand

from app.models import Book


PRODUCTS = [
    {
        "title": "Ao khoac gio nam Urban Fit",
        "author": "Urban Fit",
        "category": "quan_ao",
        "description": "Ao khoac chong gio chat lieu nhe, phu hop di hoc va di lam.",
        "image_url": "https://images.unsplash.com/photo-1521572163474-6864f9cf17ab",
        "price": Decimal("399000"),
        "stock": 45,
    },
    {
        "title": "Vay midi nu Linen Soft",
        "author": "Linen Soft",
        "category": "quan_ao",
        "description": "Vay midi thoang mat, phu hop di choi cuoi tuan.",
        "image_url": "https://images.unsplash.com/photo-1496747611176-843222e1e57c",
        "price": Decimal("459000"),
        "stock": 30,
    },
    {
        "title": "May xay sinh to SmartBlend 700W",
        "author": "SmartHome",
        "category": "gia_dung",
        "description": "May xay da nang 3 toc do, coi thuy tinh day dan.",
        "image_url": "https://images.unsplash.com/photo-1570222094114-d054a817e56b",
        "price": Decimal("890000"),
        "stock": 28,
    },
    {
        "title": "Noi chien khong dau AirChef 6L",
        "author": "AirChef",
        "category": "gia_dung",
        "description": "Noi chien 6L dieu khien cam ung, tiet kiem thoi gian nau.",
        "image_url": "https://images.unsplash.com/photo-1585515656240-2f8a6fbbf468",
        "price": Decimal("1690000"),
        "stock": 24,
    },
    {
        "title": "Tai nghe Bluetooth NoiseFree X2",
        "author": "NoiseFree",
        "category": "dien_tu",
        "description": "Tai nghe chong on chu dong, pin toi da 35 gio.",
        "image_url": "https://images.unsplash.com/photo-1505740420928-5e560c06d30e",
        "price": Decimal("1290000"),
        "stock": 40,
    },
    {
        "title": "Laptop WorkPro 14 inch i5",
        "author": "WorkPro",
        "category": "dien_tu",
        "description": "Laptop van phong 14 inch, SSD 512GB, RAM 16GB.",
        "image_url": "https://images.unsplash.com/photo-1496181133206-80ce9b88a853",
        "price": Decimal("17990000"),
        "stock": 12,
    },
    {
        "title": "Sach: Tu duy nhanh va cham",
        "author": "Daniel Kahneman",
        "category": "sach",
        "description": "Tac pham noi tieng ve tam ly hoc hanh vi va ra quyet dinh.",
        "image_url": "https://images.unsplash.com/photo-1544716278-ca5e3f4abd8c",
        "price": Decimal("189000"),
        "stock": 60,
    },
    {
        "title": "Sach: Nha gia kim",
        "author": "Paulo Coelho",
        "category": "sach",
        "description": "Tieu thuyet truyen cam hung cho hanh trinh theo duoi uoc mo.",
        "image_url": "https://images.unsplash.com/photo-1512820790803-83ca734da794",
        "price": Decimal("99000"),
        "stock": 85,
    },
]


class Command(BaseCommand):
    help = "Seed du lieu san pham mau da nganh."

    def handle(self, *args, **options):
        for payload in PRODUCTS:
            Book.objects.update_or_create(
                title=payload["title"],
                defaults=payload,
            )

        self.stdout.write(self.style.SUCCESS(f"Da dong bo {len(PRODUCTS)} san pham mau."))
