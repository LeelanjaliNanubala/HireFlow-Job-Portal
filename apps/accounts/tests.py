from django.test import TestCase
from django.urls import reverse

from apps.common.factories import PASSWORD, make_admin, make_candidate, make_recruiter

from .models import User


class UserModelTests(TestCase):
    def test_password_is_hashed_and_email_is_lowercased(self):
        user = User.objects.create_user(email='Mixed@Example.COM', password=PASSWORD, full_name='A')
        self.assertEqual(user.email, 'mixed@example.com')
        self.assertNotEqual(user.password, PASSWORD)
        self.assertTrue(user.check_password(PASSWORD))

    def test_superuser_gets_admin_role(self):
        self.assertEqual(make_admin().role, User.Role.ADMIN)


class RegistrationTests(TestCase):
    def test_candidate_registration_creates_profile_and_logs_in(self):
        response = self.client.post(reverse('accounts:register_candidate'), {
            'full_name': 'Asha Rao', 'email': 'asha@example.com', 'phone': '999',
            'password1': PASSWORD, 'password2': PASSWORD})
        self.assertRedirects(response, reverse('candidates:profile'))
        user = User.objects.get(email='asha@example.com')
        self.assertEqual(user.role, User.Role.CANDIDATE)
        self.assertTrue(hasattr(user, 'candidate_profile'))

    def test_recruiter_registration_creates_pending_company(self):
        self.client.post(reverse('accounts:register_recruiter'), {
            'full_name': 'Ravi', 'email': 'ravi@example.com', 'company_name': 'NewCo', 'designation': 'HR',
            'password1': PASSWORD, 'password2': PASSWORD})
        user = User.objects.get(email='ravi@example.com')
        self.assertEqual(user.role, User.Role.RECRUITER)
        self.assertEqual(user.recruiter_profile.company.name, 'NewCo')
        self.assertFalse(user.recruiter_profile.company.is_verified)

    def test_duplicate_email_and_password_mismatch_rejected(self):
        make_candidate(email='dup@example.com')
        response = self.client.post(reverse('accounts:register_candidate'), {
            'full_name': 'X', 'email': 'DUP@example.com', 'password1': PASSWORD, 'password2': 'different'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(User.objects.filter(email__iexact='dup@example.com').count(), 1)


class LoginAndRoleTests(TestCase):
    def test_login_redirects_by_role(self):
        make_candidate()
        make_recruiter()
        make_admin()
        expectations = {
            'candidate@example.com': reverse('candidates:dashboard'),
            'recruiter@example.com': reverse('analytics:recruiter_dashboard'),
            'admin@example.com': reverse('analytics:admin_dashboard'),
        }
        for email, target in expectations.items():
            response = self.client.post(reverse('accounts:login'), {'username': email, 'password': PASSWORD})
            self.assertRedirects(response, reverse('accounts:dashboard'), fetch_redirect_response=False)
            self.assertRedirects(self.client.get(reverse('accounts:dashboard')), target,
                                 fetch_redirect_response=False)
            self.client.post(reverse('accounts:logout'))

    def test_wrong_password_fails(self):
        make_candidate()
        response = self.client.post(reverse('accounts:login'),
                                    {'username': 'candidate@example.com', 'password': 'nope'})
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_role_pages_are_protected(self):
        make_candidate()
        self.client.login(username='candidate@example.com', password=PASSWORD)
        self.assertEqual(self.client.get(reverse('analytics:admin_dashboard')).status_code, 403)
        self.assertEqual(self.client.get(reverse('jobs:manage')).status_code, 403)

    def test_anonymous_is_sent_to_login(self):
        response = self.client.get(reverse('candidates:dashboard'))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('accounts:login'), response.url)

    def test_logout_requires_post(self):
        make_candidate()
        self.client.login(username='candidate@example.com', password=PASSWORD)
        self.assertEqual(self.client.get(reverse('accounts:logout')).status_code, 405)


class PasswordResetTests(TestCase):
    def test_reset_email_is_sent(self):
        from django.core import mail
        make_candidate()
        response = self.client.post(reverse('accounts:password_reset'), {'email': 'candidate@example.com'})
        self.assertRedirects(response, reverse('accounts:password_reset_done'))
        self.assertEqual(len(mail.outbox), 1)
