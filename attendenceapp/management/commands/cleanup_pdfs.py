import os
import time
from django.core.management.base import BaseCommand
from django.conf import settings

class Command(BaseCommand):
    help = 'Deletes PDF reports older than X days'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=2,  # default: delete files older than 7 days
            help='Delete PDFs older than this many days',
        )

    def handle(self, *args, **options):
        days = options['days']
        now = time.time()
        cutoff = now - (days * 86400)  # 86400 seconds in a day

        reports_dir = os.path.join(settings.MEDIA_ROOT, 'reports')
        if not os.path.exists(reports_dir):
            self.stdout.write(self.style.WARNING(f"Reports directory {reports_dir} does not exist."))
            return

        deleted_files = 0
        for filename in os.listdir(reports_dir):
            if filename.lower().endswith('.pdf'):
                filepath = os.path.join(reports_dir, filename)
                if os.path.isfile(filepath) and os.path.getmtime(filepath) < cutoff:
                    os.remove(filepath)
                    deleted_files += 1

        self.stdout.write(self.style.SUCCESS(f"Deleted {deleted_files} PDF(s) older than {days} days."))
