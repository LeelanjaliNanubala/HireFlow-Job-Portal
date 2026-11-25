from django.contrib import admin

from .models import CandidateProfile, CandidateSkill, Education, Resume, SavedJob, Skill, WorkExperience


@admin.register(CandidateProfile)
class CandidateProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'location', 'headline', 'created_at')
    search_fields = ('user__email', 'user__full_name', 'location')


@admin.register(Skill)
class SkillAdmin(admin.ModelAdmin):
    search_fields = ('name',)


@admin.register(Resume)
class ResumeAdmin(admin.ModelAdmin):
    list_display = ('original_name', 'candidate', 'file_type', 'file_size', 'uploaded_at')


admin.site.register(Education)
admin.site.register(WorkExperience)
admin.site.register(CandidateSkill)
admin.site.register(SavedJob)
