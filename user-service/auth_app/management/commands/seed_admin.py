import os

from django.contrib.auth.management import get_default_username
from django.contrib.auth.models import Group, User
from django.core.management.base import BaseCommand

ROLE_ADMIN = 'Admin'
ROLE_STAFF = 'Staff'
ROLE_CUSTOMER = 'Customer'


class Command(BaseCommand):
    help = 'Create or update default admin account for user-service auth.'

    def handle(self, *args, **options):
        username = os.getenv('AUTH_ADMIN_USERNAME', get_default_username())
        email = os.getenv('AUTH_ADMIN_EMAIL', 'admin@bookstore.local')
        password = os.getenv('AUTH_ADMIN_PASSWORD', 'Admin@123456')

        for role in [ROLE_ADMIN, ROLE_STAFF, ROLE_CUSTOMER]:
            Group.objects.get_or_create(name=role)

        user = User.objects.filter(username=username).first()
        if not user:
            user = User.objects.create_superuser(username=username, email=email, password=password)
            self.stdout.write(self.style.SUCCESS(f'Created admin user: {username}'))
        else:
            user.email = email
            if password:
                user.set_password(password)
            user.is_staff = True
            user.is_superuser = True
            user.save(update_fields=['email', 'password', 'is_staff', 'is_superuser'])
            self.stdout.write(self.style.WARNING(f'Updated existing admin user: {username}'))

        groups = Group.objects.filter(name__in=[ROLE_ADMIN, ROLE_STAFF, ROLE_CUSTOMER])
        user.groups.remove(*groups)
        user.groups.add(Group.objects.get(name=ROLE_ADMIN))
        self.stdout.write(self.style.SUCCESS('Admin role assignment ensured.'))
