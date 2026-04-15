from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone

from tracker.models import DailyEntry, EntryItem
from tracker.models import Member


class Command(BaseCommand):
    help = 'Seed demo data (members, entries, and a demo login user)'

    def handle(self, *args, **options):
        User = get_user_model()
        demo_username = 'demo'
        demo_password = 'Demo@12345'
        demo_email = 'demo@example.com'

        user, created = User.objects.get_or_create(
            username=demo_username,
            defaults={'email': demo_email, 'is_staff': False, 'is_superuser': False},
        )
        user.email = demo_email
        user.is_staff = False
        user.is_superuser = False
        user.set_password(demo_password)
        user.save()
        self.stdout.write(self.style.SUCCESS(
            f"Demo login {'created' if created else 'updated'}: username={demo_username} password={demo_password}"
        ))

        members = ['Shruti Jain', 'Niharika K', 'Shivendra', 'Archita', 'Santhosh', 'Vishal']
        member_objs = []
        for name in members:
            m, created = Member.objects.get_or_create(display_name=name)
            member_objs.append(m)
            status = 'created' if created else 'exists'
            self.stdout.write(f'  {status}: {name}')

        # Create a few sample entries for the last 5 days (idempotent per day/member/kind)
        today = timezone.localdate()
        kinds = ['plan', 'update']
        for i in range(5):
            d = today - timezone.timedelta(days=i)
            for idx, m in enumerate(member_objs[:3]):  # keep it small
                kind = kinds[(i + idx) % 2]
                entry, _ = DailyEntry.objects.get_or_create(
                    entry_date=d,
                    kind=kind,
                    member=m,
                    defaults={'status': 'open', 'raw_text': f'{kind.title()} for {d.isoformat()}', 'source': 'seed'},
                )
                # Ensure at least 2 items
                if entry.items.count() == 0:
                    EntryItem.objects.create(entry=entry, task_type='Content Creation', question_type='Subjective', customer='Internal', count=2, notes='Seeded')
                    EntryItem.objects.create(entry=entry, task_type='Content Review', question_type='Multiple Choice', customer='Internal', count=1, notes='Seeded')

        self.stdout.write(self.style.SUCCESS('Done.'))
