"""Template helpers: status badge colours and pagination links."""
from django import template

register = template.Library()

STATUS_CLASSES = {
    # applications
    'submitted': 'bg-secondary',
    'under_review': 'bg-info text-dark',
    'shortlisted': 'bg-primary',
    'interview_scheduled': 'bg-warning text-dark',
    'interview_completed': 'bg-dark',
    'selected': 'bg-success',
    'rejected': 'bg-danger',
    'withdrawn': 'bg-secondary',
    # jobs
    'draft': 'bg-secondary',
    'published': 'bg-success',
    'paused': 'bg-warning text-dark',
    'closed': 'bg-dark',
    # company verification
    'pending': 'bg-warning text-dark',
    'verified': 'bg-success',
    # interviews
    'scheduled': 'bg-primary',
    'completed': 'bg-success',
    'cancelled': 'bg-danger',
    'no_show': 'bg-warning text-dark',
}


@register.filter
def status_class(value):
    """{{ app.status|status_class }} -> Bootstrap badge colour classes."""
    return STATUS_CLASSES.get(str(value), 'bg-secondary')


@register.simple_tag(takes_context=True)
def url_replace(context, **kwargs):
    """Keep the current search filters while changing one value, e.g. the page number."""
    query = context['request'].GET.copy()
    for key, value in kwargs.items():
        if value in (None, ''):
            query.pop(key, None)
        else:
            query[key] = str(value)
    return query.urlencode()


@register.filter
def status_label(value):
    """'under_review' -> 'Under Review' (used for history rows that store raw status values)."""
    return str(value).replace('_', ' ').title()
