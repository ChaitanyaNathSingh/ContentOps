from django.contrib import admin
from .models import DailyEntry, EntryItem, Member, AEDailyUpdate


class EntryItemInline(admin.TabularInline):
    model = EntryItem
    extra = 0


@admin.register(Member)
class MemberAdmin(admin.ModelAdmin):
    list_display = ('display_name', 'role', 'is_active', 'created_at')
    list_filter = ('is_active', 'role')
    search_fields = ('display_name',)


@admin.register(DailyEntry)
class DailyEntryAdmin(admin.ModelAdmin):
    list_display = ('entry_date', 'kind', 'status', 'member', 'source', 'created_at')
    list_filter = ('kind', 'status', 'entry_date')
    search_fields = ('raw_text', 'member__display_name')
    date_hierarchy = 'entry_date'
    inlines = [EntryItemInline]


@admin.register(AEDailyUpdate)
class AEDailyUpdateAdmin(admin.ModelAdmin):
    list_display = ('entry_date', 'member', 'setter_enhancements', 'bug_fixes', 'deployments', 'updated_at')
    list_filter = ('entry_date', 'member')
    search_fields = ('member__display_name',)
    date_hierarchy = 'entry_date'
