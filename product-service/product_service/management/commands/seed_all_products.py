import importlib

from django.core.management.base import BaseCommand


APP_SEEDERS = [
    "book_app",
    "beauty_app",
    "electronics_app",
    "fashion_app",
    "grocery_app",
    "household_app",
    "laptop_app",
    "mobile_app",
    "sports_app",
]


class Command(BaseCommand):
    help = "Seed demo data for all product categories."

    def handle(self, *args, **options):
        for app in APP_SEEDERS:
            module_path = f"{app}.management.commands.seed_products"
            try:
                module = importlib.import_module(module_path)
                module.Command().handle()
                self.stdout.write(self.style.SUCCESS(f"Seeded products for {app}."))
            except Exception as exc:
                self.stdout.write(self.style.ERROR(f"Failed to seed {app}: {exc}"))
