from django import forms
from django.forms import formset_factory
from .models import DailyEntry, EntryItem, AEDailyUpdate

_cls = 'field'

QUESTION_TYPE_CHOICES = [('', '— select type —')] + EntryItem.QUESTION_TYPE_CHOICES

# Canonical work-type choices used across Plan and Extra-work forms.
TASK_TYPE_CHOICES = [
    ('', '— select work type —'),
    ('Internal meeting', 'Internal meeting'),
    ('Assessment creation', 'Assessment creation'),
    ('Others', 'Others'),
    ('Content review', 'Content review'),
    ('Documentation', 'Documentation'),
    ('Content creation and development', 'Content creation and development'),
    ('Content refixing', 'Content refixing'),
    ('External meeting', 'External meeting'),
    ('Content manual-audit', 'Content manual-audit'),
    ('Content feedback analysis', 'Content feedback analysis'),
    ('Other', 'Other…'),
]


class DailyEntryForm(forms.ModelForm):
    class Meta:
        model = DailyEntry
        fields = ['member', 'entry_date', 'status', 'raw_text']
        widgets = {
            'member': forms.Select(attrs={'class': _cls}),
            'entry_date': forms.DateInput(attrs={'type': 'date', 'class': _cls}),
            'status': forms.Select(attrs={'class': _cls}),
            'raw_text': forms.Textarea(attrs={
                'rows': 3,
                'class': _cls,
                'placeholder': 'Optional: paste raw message or summary',
            }),
        }


class EntryItemForm(forms.Form):
    """Used for Plan tasks and Extra-work rows (both creation and update)."""

    task_type = forms.ChoiceField(
        choices=TASK_TYPE_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': _cls}),
    )
    question_type = forms.ChoiceField(
        choices=QUESTION_TYPE_CHOICES, required=False,
        widget=forms.Select(attrs={'class': _cls}),
    )
    customer = forms.CharField(
        max_length=120, required=False,
        widget=forms.TextInput(attrs={'class': _cls, 'placeholder': 'e.g. CleverTap'}),
    )
    count = forms.IntegerField(
        min_value=1, required=False,
        widget=forms.NumberInput(attrs={'class': _cls, 'placeholder': '0'}),
    )
    due_at = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': _cls}),
    )
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'rows': 2, 'class': _cls, 'placeholder': 'Notes / comment'}),
    )
    status = forms.ChoiceField(
        choices=DailyEntry.STATUS_CHOICES,
        required=False,
        initial='open',
        widget=forms.Select(attrs={'class': _cls}),
    )


EntryItemFormSet = formset_factory(
    EntryItemForm,
    extra=2,
    can_delete=True,
    max_num=40,
    validate_max=True,
)

# Used on Update screen for the optional "Extra work" section.
ExtraEntryItemFormSet = formset_factory(
    EntryItemForm,
    extra=1,
    can_delete=True,
    max_num=40,
    validate_max=True,
)


class PlanUpdateLineForm(forms.Form):
    """One row per plan task when filing a daily update."""

    plan_item_id = forms.IntegerField(widget=forms.HiddenInput)
    status = forms.ChoiceField(
        choices=EntryItem.STATUS_CHOICES,
        widget=forms.Select(attrs={'class': _cls}),
    )
    count = forms.IntegerField(
        required=False,
        min_value=1,
        widget=forms.NumberInput(attrs={'class': _cls, 'placeholder': 'Count'}),
    )
    notes = forms.CharField(
        required=True,
        widget=forms.Textarea(attrs={'rows': 2, 'class': _cls, 'placeholder': 'Progress / blockers'}),
    )
    due_at = forms.DateField(
        required=True,
        widget=forms.DateInput(attrs={'type': 'date', 'class': _cls}),
        help_text="Required by Jira workflow for transitions.",
    )


PlanUpdateLineFormSet = formset_factory(
    PlanUpdateLineForm,
    extra=0,
    min_num=0,
    validate_min=False,
)


class AEDailyUpdateForm(forms.ModelForm):
    class Meta:
        model = AEDailyUpdate
        fields = [
            'member', 'entry_date',
            'setter_enhancements',
            'he_support_replies',
            'eng_assessment_replies',
            'facecode_replies',
            'data_requests_replies',
            'redash_queries',
            'bug_fixes',
            'deployments',
            'setter_enhancements_count',
            'utilities',
            'notes',
        ]
        widgets = {
            'member': forms.Select(attrs={'class': _cls}),
            'entry_date': forms.DateInput(attrs={'type': 'date', 'class': _cls}),
            'setter_enhancements': forms.NumberInput(attrs={'class': _cls, 'min': 0}),
            'he_support_replies': forms.NumberInput(attrs={'class': _cls, 'min': 0}),
            'eng_assessment_replies': forms.NumberInput(attrs={'class': _cls, 'min': 0}),
            'facecode_replies': forms.NumberInput(attrs={'class': _cls, 'min': 0}),
            'data_requests_replies': forms.NumberInput(attrs={'class': _cls, 'min': 0}),
            'redash_queries': forms.NumberInput(attrs={'class': _cls, 'min': 0}),
            'bug_fixes': forms.NumberInput(attrs={'class': _cls, 'min': 0}),
            'deployments': forms.NumberInput(attrs={'class': _cls, 'min': 0}),
            'setter_enhancements_count': forms.NumberInput(attrs={'class': _cls, 'min': 0}),
            'utilities': forms.NumberInput(attrs={'class': _cls, 'min': 0}),
            'notes': forms.Textarea(attrs={'rows': 3, 'class': _cls, 'placeholder': 'Optional notes'}),
        }
        labels = {
            'setter_enhancements': 'Setter Enhancements',
            'he_support_replies': '#he_support_v2 Replies / Resolutions',
            'eng_assessment_replies': '#engineering_assessment Replies / Resolutions',
            'facecode_replies': '#engineering_facecode Replies / Resolutions',
            'data_requests_replies': '#data_requests Replies / Resolutions',
            'redash_queries': 'Redash Queries',
            'bug_fixes': 'Bug Fixes',
            'deployments': 'Deployments',
            'setter_enhancements_count': 'Setter Enhancements (count)',
            'utilities': 'Utilities',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from .models import Member
        self.fields['member'].queryset = Member.objects.filter(is_active=True, role='ae')
