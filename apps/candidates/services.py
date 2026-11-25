"""Candidate business logic."""
from .models import CandidateProfile, Skill


def get_profile(user):
    """The candidate profile of the logged-in user (created if it is missing)."""
    profile, _ = CandidateProfile.objects.get_or_create(user=user)
    return profile


def get_or_create_skill(name):
    """Skills are shared by candidates and jobs. 'python' and 'Python' are the same skill."""
    name = ' '.join(name.split())[:60]
    skill = Skill.objects.filter(name__iexact=name).first()
    return skill or Skill.objects.create(name=name)


def can_download_resume(user, resume):
    """Who may download a resume: its owner, an admin, or a recruiter of a company the candidate applied to."""
    if not user.is_authenticated:
        return False
    if user.role == 'admin':
        return True
    if user.role == 'candidate':
        return resume.candidate.user_id == user.id
    if user.role == 'recruiter':
        profile = getattr(user, 'recruiter_profile', None)
        if profile is None or profile.company_id is None:
            return False
        from apps.applications.models import JobApplication
        return JobApplication.objects.filter(resume=resume, job__company_id=profile.company_id).exists()
    return False
