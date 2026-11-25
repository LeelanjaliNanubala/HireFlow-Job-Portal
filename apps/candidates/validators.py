"""Resume upload validation: extension, size and real file content."""
import os

from django.conf import settings
from django.core.exceptions import ValidationError

# Allowed extensions and the first bytes ("magic numbers") a real file of that type starts with.
ALLOWED_SIGNATURES = {
    '.pdf': [b'%PDF'],
    '.docx': [b'PK\x03\x04'],
    '.doc': [b'\xd0\xcf\x11\xe0'],
}


def validate_resume_file(upload):
    extension = os.path.splitext(upload.name)[1].lower()
    if extension not in ALLOWED_SIGNATURES:
        raise ValidationError('Only PDF, DOC and DOCX files are allowed.')
    max_bytes = settings.MAX_RESUME_SIZE_MB * 1024 * 1024
    if upload.size > max_bytes:
        raise ValidationError(f'The file is too large. Maximum size is {settings.MAX_RESUME_SIZE_MB} MB.')
    if upload.size == 0:
        raise ValidationError('The file is empty.')
    upload.seek(0)
    head = upload.read(8)
    upload.seek(0)
    if not any(head.startswith(signature) for signature in ALLOWED_SIGNATURES[extension]):
        raise ValidationError('The file content does not match its extension.')
