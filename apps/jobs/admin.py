from django.contrib import admin

from .models import Job, JobSkill


class JobSkillInline(admin.TabularInline):
    model = JobSkill
    extra = 0


@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    list_display = ('title', 'company', 'location', 'status', 'deadline', 'is_featured', 'is_hidden_by_admin')
    list_filter = ('status', 'employment_type', 'is_featured', 'is_hidden_by_admin')
    search_fields = ('title', 'company__name')
    inlines = [JobSkillInline]
