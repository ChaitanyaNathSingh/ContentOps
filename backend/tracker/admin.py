from django.contrib import admin
from .models import DailyEntry, EntryItem, Member


class EntryItemInline(admin.TabularInline):
    model = EntryItem
    extra = 0


@admin.register(Member)
class MemberAdmin(admin.ModelAdmin):
    list_display = ('display_name', 'is_active', 'created_at')
    list_filter = ('is_active',)
    search_fields = ('display_name',)


@admin.register(DailyEntry)
class DailyEntryAdmin(admin.ModelAdmin):
    list_display = ('entry_date', 'kind', 'status', 'member', 'source', 'created_at')
    list_filter = ('kind', 'status', 'entry_date')
    search_fields = ('raw_text', 'member__display_name')
    date_hierarchy = 'entry_date'
    inlines = [EntryItemInline]
