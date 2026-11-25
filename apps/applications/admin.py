from django.contrib import admin

from .models import ApplicationHistory, JobApplication


class HistoryInline(admin.TabularInline):
    model = ApplicationHistory
    extra = 0
    readonly_fields = ('changed_by', 'old_status', 'new_status', 'note', 'changed_at')
    can_delete = False


@admin.register(JobApplication)
class JobApplicationAdmin(admin.ModelAdmin):
    list_display = ('id', 'candidate', 'job', 'status', 'applied_at')
    list_filter = ('status',)
    search_fields = ('candidate__user__email', 'job__title')
    inlines = [HistoryInline]
