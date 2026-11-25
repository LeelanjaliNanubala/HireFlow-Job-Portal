from django.contrib import admin

from .models import Company, RecruiterProfile


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ('name', 'industry', 'location', 'verification_status', 'created_at')
    list_filter = ('verification_status',)
    search_fields = ('name',)


@admin.register(RecruiterProfile)
class RecruiterProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'company', 'designation')
    search_fields = ('user__email', 'company__name')
