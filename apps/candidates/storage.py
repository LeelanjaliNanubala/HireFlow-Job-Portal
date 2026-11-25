"""Private storage for resumes."""
from django.core.files.storage import FileSystemStorage


class PrivateStorage(FileSystemStorage):
    """Stores files under settings.MEDIA_ROOT (media_private/) and NEVER gives out a public URL."""

    def url(self, name):
        raise ValueError('Private files cannot be opened through a URL. Use the download view.')


def get_private_storage():
    return PrivateStorage()
