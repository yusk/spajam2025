# core/management/commands/createspecifiedsuperuser.py

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Create a superuser with specified username, email, and password (defaults included)."

    def add_arguments(self, parser):
        parser.add_argument("--name", type=str, default="test", help="Username for the superuser (default: test)")
        parser.add_argument(
            "--email",
            type=str,
            default="test@test.com",
            help="Email address for the superuser (default: test@test.com)",
        )
        parser.add_argument(
            "--password", type=str, default="testuser", help="Password for the superuser (default: testuser)"
        )

    def handle(self, *args, **options):
        User = get_user_model()

        name = options["name"]
        email = options["email"]
        password = options["password"]

        # 既に存在する場合はスキップ
        if User.objects.filter(name=name).exists():
            self.stdout.write(self.style.WARNING(f"User '{name}' already exists. Skipping."))
            return

        User.objects.create_superuser(name=name, email=email, password=password)
        self.stdout.write(self.style.SUCCESS(f"Superuser '{name}' created successfully."))
