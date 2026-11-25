from django.test import TestCase
from django.urls import reverse

from apps.common.factories import PASSWORD, make_candidate

from .models import Notification
from .services import notify


class NotificationTests(TestCase):
    def setUp(self):
        self.user, _ = make_candidate()
        self.client.login(username='candidate@example.com', password=PASSWORD)

    def test_unread_count_in_context_and_mark_all_read(self):
        notify(self.user, 'One', 'First')
        notify(self.user, 'Two', 'Second')
        response = self.client.get(reverse('notifications:list'))
        self.assertEqual(response.context['unread_notification_count'], 2)
        self.client.post(reverse('notifications:mark_all_read'))
        self.assertEqual(Notification.objects.filter(user=self.user, is_read=False).count(), 0)

    def test_open_marks_read_and_redirects(self):
        item = notify(self.user, 'Go', 'Msg', link=reverse('applications:mine'))
        response = self.client.get(reverse('notifications:open', args=[item.pk]))
        self.assertRedirects(response, reverse('applications:mine'))
        item.refresh_from_db()
        self.assertTrue(item.is_read)

    def test_cannot_open_someone_elses_notification(self):
        other, _ = make_candidate(email='other@example.com')
        item = notify(other, 'Private', 'Msg')
        self.assertEqual(self.client.get(reverse('notifications:open', args=[item.pk])).status_code, 404)

    def test_email_disabled_by_default(self):
        from django.core import mail
        notify(self.user, 'No email', 'Body')
        self.assertEqual(len(mail.outbox), 0)
