"""Account business logic shared by web forms and the REST API."""
from django.db import transaction

from apps.candidates.models import CandidateProfile
from apps.companies.models import Company, RecruiterProfile

from .models import User


@transaction.atomic
def register_user(*, role, full_name, email, password, phone='', company_name='', designation=''):
    """Create a user plus the matching profile in ONE database transaction."""
    user = User.objects.create_user(email=email, password=password, full_name=full_name, role=role)
    if role == User.Role.CANDIDATE:
        CandidateProfile.objects.create(user=user, phone=phone)
    else:
        company = Company.objects.create(name=company_name)  # starts as "pending verification"
        RecruiterProfile.objects.create(user=user, company=company, designation=designation)
    return user
