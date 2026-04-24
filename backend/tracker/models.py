from django.db import models


class Member(models.Model):
    ROLE_CHOICES = [
        ('content', 'Content'),
        ('ae', 'Application Engineer'),
    ]

    display_name = models.CharField(max_length=120, unique=True)
    slack_user_id = models.CharField(max_length=64, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='content')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['display_name']

    def __str__(self):
        return self.display_name


class DailyEntry(models.Model):
    KIND_CHOICES = [('plan', 'Plan'), ('update', 'Update')]
    STATUS_CHOICES = [
        ('open', 'Open'),
        ('in_progress', 'In Progress'),
        ('blocked', 'Blocked'),
        ('closed', 'Closed'),
    ]

    entry_date = models.DateField()
    kind = models.CharField(max_length=12, choices=KIND_CHOICES)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default='open')
    member = models.ForeignKey(Member, on_delete=models.PROTECT, related_name='entries')
    raw_text = models.TextField(blank=True, null=True)
    source = models.CharField(max_length=32, default='web')
    jira_issue_key = models.CharField(max_length=32, blank=True, null=True)
    jira_issue_url = models.URLField(blank=True, null=True, max_length=500)
    slack_reply_ts = models.CharField(
        max_length=32, blank=True, null=True,
        help_text="Slack ts of thread reply for this entry (if posted)",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['entry_date', 'kind']),
            models.Index(fields=['member', 'entry_date']),
        ]
        ordering = ['-entry_date', '-created_at']

    def __str__(self):
        return f"{self.entry_date} · {self.member} · {self.kind}"


class EntryItem(models.Model):
    STATUS_CHOICES = DailyEntry.STATUS_CHOICES

    QUESTION_TYPE_CHOICES = [
        ('Programming', 'Programming'),
        ('SQL', 'SQL'),
        ('Frontend', 'Frontend'),
        ('Full Stack', 'Full Stack'),
        ('Automation Testing', 'Automation Testing'),
        ('DevOps', 'DevOps'),
        ('Machine Learning', 'Machine Learning'),
        ('Diagram', 'Diagram'),
        ('Data Science', 'Data Science'),
        ('File Upload', 'File Upload'),
        ('Project', 'Project'),
        ('Java Project', 'Java Project'),
        ('C# Project', 'C# Project'),
        ('Python Project', 'Python Project'),
        ('Subjective', 'Subjective'),
        ('Multiple Choice', 'Multiple Choice'),
        ('Approximate', 'Approximate'),
        ('Golf', 'Golf'),
        ('RegExp', 'RegExp'),
        ('FileEval', 'FileEval'),
    ]

    entry = models.ForeignKey(DailyEntry, on_delete=models.CASCADE, related_name='items')
    plan_item = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='update_lines',
        help_text='Plan task this update row refers to (updates only).',
    )
    task_type = models.CharField(max_length=120)
    question_type = models.CharField(max_length=120, blank=True, null=True, choices=QUESTION_TYPE_CHOICES)
    customer = models.CharField(max_length=120, blank=True, null=True)
    count = models.PositiveIntegerField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    due_at = models.DateField(blank=True, null=True)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default='open')
    jira_issue_key = models.CharField(max_length=32, blank=True, null=True)
    jira_issue_url = models.URLField(blank=True, null=True, max_length=500)

    def __str__(self):
        return f"{self.task_type} ({self.question_type or '—'})"


class AEDailyUpdate(models.Model):
    """Daily update entry for Application Engineers — one row per member per day."""

    member = models.ForeignKey(Member, on_delete=models.PROTECT, related_name='ae_daily_updates')
    entry_date = models.DateField()
    setter_enhancements = models.PositiveIntegerField(default=0)
    he_support_replies = models.PositiveIntegerField(default=0, verbose_name='#he_support_v2 Replies/Resolutions')
    eng_assessment_replies = models.PositiveIntegerField(default=0, verbose_name='#engineering_assessment Replies/Resolutions')
    facecode_replies = models.PositiveIntegerField(default=0, verbose_name='#engineering_facecode Replies/Resolutions')
    data_requests_replies = models.PositiveIntegerField(default=0, verbose_name='#data_requests Replies/Resolutions')
    redash_queries = models.PositiveIntegerField(default=0)
    bug_fixes = models.PositiveIntegerField(default=0)
    deployments = models.PositiveIntegerField(default=0)
    setter_enhancements_count = models.PositiveIntegerField(default=0, verbose_name='Setter Enhancements (count)')
    utilities = models.PositiveIntegerField(default=0)
    bug_bounty_reviewed = models.PositiveIntegerField(default=0, verbose_name='Bug Bounty Reviewed')
    notes = models.TextField(blank=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-entry_date', 'member__display_name']
        unique_together = [('member', 'entry_date')]
        indexes = [models.Index(fields=['entry_date'])]

    def __str__(self):
        return f"{self.entry_date} · {self.member}"


class SlackDayThread(models.Model):
    """One Slack parent message per calendar day and kind (plan vs update)."""

    digest_date = models.DateField()
    kind = models.CharField(max_length=12)
    channel = models.CharField(max_length=120, default="")
    parent_ts = models.CharField(
        max_length=32, blank=True, null=True,
        help_text="Slack message ts of the parent (thread root)",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["digest_date", "kind"],
                name="unique_slack_digest_date_kind",
            ),
        ]

    def __str__(self):
        return f"{self.digest_date} {self.kind}"
