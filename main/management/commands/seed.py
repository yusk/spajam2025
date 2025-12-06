from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "seed"

    def add_arguments(self, parser):
        parser.add_argument(dest="prompt", help="prompt")

    def handle(self, *args, **options):
        print("seed")
