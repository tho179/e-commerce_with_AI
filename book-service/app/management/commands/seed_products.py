from decimal import Decimal

from django.core.management.base import BaseCommand

from app.models import Book


PRODUCTS = [
    {
        "title": "Tư duy nhanh và chậm",
        "author": "Daniel Kahneman",
        "category": "sach",
        "description": "Tác phẩm kinh điển về tâm lý học hành vi và quá trình ra quyết định.",
        "image_url": "https://images.unsplash.com/photo-1544716278-ca5e3f4abd8c",
        "price": Decimal("189000"),
        "stock": 90,
    },
    {
        "title": "Nhà giả kim",
        "author": "Paulo Coelho",
        "category": "sach",
        "description": "Tiểu thuyết truyền cảm hứng về hành trình theo đuổi ước mơ.",
        "image_url": "https://images.unsplash.com/photo-1512820790803-83ca734da794",
        "price": Decimal("99000"),
        "stock": 120,
    },
    {
        "title": "Đắc nhân tâm",
        "author": "Dale Carnegie",
        "category": "sach",
        "description": "Cuốn sách kinh điển về nghệ thuật giao tiếp và đối nhân xử thế.",
        "image_url": "https://images.unsplash.com/photo-1481627834876-b7833e8f5570",
        "price": Decimal("119000"),
        "stock": 80,
    },
    {
        "title": "Muôn kiếp nhân sinh",
        "author": "Nguyên Phong",
        "category": "sach",
        "description": "Tác phẩm về nhân sinh quan và hành trình khám phá bản thân.",
        "image_url": "https://images.unsplash.com/photo-1495446815901-a7297e633e8d",
        "price": Decimal("168000"),
        "stock": 75,
    },
    {
        "title": "Lược sử thời gian",
        "author": "Stephen Hawking",
        "category": "sach",
        "description": "Cuốn sách khoa học phổ thông nổi tiếng về vũ trụ học.",
        "image_url": "https://images.unsplash.com/photo-1519682337058-a94d519337bc",
        "price": Decimal("149000"),
        "stock": 64,
    },
    {
        "title": "Tuổi trẻ đáng giá bao nhiêu",
        "author": "Rosie Nguyễn",
        "category": "sach",
        "description": "Tản văn truyền cảm hứng cho người trẻ về học tập và trưởng thành.",
        "image_url": "https://images.unsplash.com/photo-1516979187457-637abb4f9353",
        "price": Decimal("109000"),
        "stock": 70,
    },
]


class Command(BaseCommand):
    help = "Seed dữ liệu sách mẫu chuẩn tiếng Việt."

    def handle(self, *args, **options):
        valid_titles = {item["title"] for item in PRODUCTS}
        Book.objects.exclude(title__in=valid_titles).delete()

        for payload in PRODUCTS:
            Book.objects.update_or_create(
                title=payload["title"],
                defaults=payload,
            )

        self.stdout.write(self.style.SUCCESS(f"Đã đồng bộ {len(PRODUCTS)} sách mẫu."))
