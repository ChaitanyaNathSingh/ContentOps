"""
Management command: post_slack_daily
Usage:
    python manage.py post_slack_daily --kind plan
    python manage.py post_slack_daily --kind update

Posts (or reuses) a parent message for the day, updates the summary, and posts
thread replies for any entries not yet posted to Slack.

Configure SLACK_BOT_TOKEN and SLACK_CHANNEL in backend/slack_config.py
"""

from datetime import date

from django.core.management.base import BaseCommand, CommandError

from tracker.models import DailyEntry, SlackDayThread
from tracker.slack_notify import (
    build_parent_text,
    format_plan_thread,
    format_update_thread,
    load_slack_config,
    slack_post,
    slack_update_message,
    _entries_for_day_kind,
)


class Command(BaseCommand):
    help = (
        'Post daily Plan or Update summary to Slack: parent + thread replies '
        '(skips entries already linked via slack_reply_ts).'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--kind',
            choices=['plan', 'update'],
            required=True,
            help='Which kind of entry to summarise: plan or update',
        )
        parser.add_argument(
            '--date',
            default=None,
            help='Date in YYYY-MM-DD format (defaults to today)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Print messages to stdout without posting to Slack',
        )

    def handle(self, *args, **options):
        kind = options['kind']
        dry_run = options['dry_run']

        if options['date']:
            try:
                from datetime import datetime
                target_date = datetime.strptime(options['date'], '%Y-%m-%d').date()
            except ValueError:
                raise CommandError('--date must be in YYYY-MM-DD format')
        else:
            target_date = date.today()

        cfg = load_slack_config()
        token = cfg.get('SLACK_BOT_TOKEN', '')
        channel = cfg.get('SLACK_CHANNEL', 'content-dashboard')

        if not dry_run:
            if not token or token.startswith('xoxb-PASTE'):
                raise CommandError(
                    'SLACK_BOT_TOKEN is not configured in backend/slack_config.py'
                )

        entries = list(_entries_for_day_kind(target_date, kind))
        if not entries:
            self.stdout.write(self.style.WARNING(
                f'No {kind} entries found for {target_date}. Nothing to post.'
            ))
            return

        parent_text = build_parent_text(target_date, kind, entries)

        if dry_run:
            self.stdout.write('\n' + '─' * 60)
            self.stdout.write(f'[DRY RUN] Parent message to #{channel}:')
            self.stdout.write(parent_text)
        else:
            thread = SlackDayThread.objects.filter(
                digest_date=target_date, kind=kind
            ).first()
            if not thread or not thread.parent_ts:
                ok, resp = slack_post(token, {'channel': channel, 'text': parent_text})
                if not ok:
                    raise CommandError(
                        f'Failed to post parent message: {resp.get("error", resp)}'
                    )
                thread_ts = resp.get('ts')
                SlackDayThread.objects.update_or_create(
                    digest_date=target_date,
                    kind=kind,
                    defaults={'channel': channel, 'parent_ts': thread_ts},
                )
                self.stdout.write(self.style.SUCCESS(
                    f'Posted parent message (ts={thread_ts})'
                ))
            else:
                ok, resp = slack_update_message(
                    token, channel, thread.parent_ts, parent_text
                )
                if not ok:
                    raise CommandError(
                        f'Failed to update parent message: {resp.get("error", resp)}'
                    )
                thread_ts = thread.parent_ts
                self.stdout.write(self.style.SUCCESS(
                    f'Updated parent message (ts={thread_ts})'
                ))

        for entry in entries:
            if entry.slack_reply_ts:
                continue
            if kind == 'plan':
                reply_text = format_plan_thread(entry)
            else:
                reply_text = format_update_thread(entry)

            if dry_run:
                self.stdout.write('\n' + '─' * 40)
                self.stdout.write(
                    f'[DRY RUN] Thread reply for {entry.member.display_name}:'
                )
                self.stdout.write(reply_text)
            else:
                ok, resp = slack_post(token, {
                    'channel': channel,
                    'thread_ts': thread_ts,
                    'text': reply_text,
                })
                if ok:
                    DailyEntry.objects.filter(pk=entry.pk).update(
                        slack_reply_ts=resp.get('ts')
                    )
                    self.stdout.write(
                        f'  ↳ Thread reply posted for {entry.member.display_name}'
                    )
                else:
                    self.stderr.write(
                        f'  ✗ Failed for {entry.member.display_name}: '
                        f'{resp.get("error")}'
                    )

        if dry_run:
            self.stdout.write('\n' + '─' * 60)
            self.stdout.write(self.style.SUCCESS('[DRY RUN] Done — no messages sent.'))
        else:
            self.stdout.write(self.style.SUCCESS(
                f'\nDone. {kind.title()} digest for {target_date} in #{channel}.'
            ))
