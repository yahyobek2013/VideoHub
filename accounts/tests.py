from io import StringIO
from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse
from django.core.management import call_command

from .forms import RegistrationForm
from .models import User


class AccountFlowTests(TestCase):
    def test_admin_bootstrap_is_repeatable_and_keeps_login_credentials(self):
        with patch.dict("os.environ", {"VH_ADMIN_PASSWORD": "ybek"}):
            call_command("ensure_videohub_admin", stdout=StringIO())
            call_command("ensure_videohub_admin", stdout=StringIO())
        admin = User.objects.get(phone="930804866")
        self.assertEqual(admin.login_name, "ybek")
        self.assertTrue(admin.is_superuser)
        self.assertTrue(admin.check_password("ybek"))
        self.assertEqual(User.objects.filter(phone="930804866").count(), 1)

    def test_registration_accepts_short_matching_password_and_hashes_it(self):
        form = RegistrationForm(data={
            "first_name": "Test User",
            "phone": "+998 90 123 45 67",
            "password1": "q",
            "password2": "q",
        })

        self.assertTrue(form.is_valid(), form.errors)
        user = form.save()
        self.assertEqual(user.phone, "+998901234567")
        self.assertNotEqual(user.password, "q")
        self.assertTrue(user.check_password("q"))

    def test_registration_rejects_mismatched_passwords(self):
        form = RegistrationForm(data={
            "first_name": "Test User",
            "phone": "+998901234568",
            "password1": "q",
            "password2": "t",
        })
        self.assertFalse(form.is_valid())
        self.assertIn("password2", form.errors)

    def test_registration_requires_name(self):
        form = RegistrationForm(data={
            "first_name": "",
            "phone": "+998901234572",
            "password1": "q",
            "password2": "q",
        })
        self.assertFalse(form.is_valid())
        self.assertIn("first_name", form.errors)

    def test_root_requires_login_and_phone_login_succeeds(self):
        response = self.client.get(reverse("splash"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Yahyobek")
        self.assertContains(response, "Yaqubboyev")

        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith(reverse("login")))

        User.objects.create_user(phone="+998901234569", password="1", first_name="Viewer")
        response = self.client.post(reverse("login"), {"phone": "+998 90 123 45 69", "password": "1"})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("home"))

    def test_login_name_alias_authenticates_the_phone_account(self):
        User.objects.create_superuser(
            phone="930804866",
            password="ybek",
            first_name="Yahyobek Yaqubboyev",
            login_name="ybek",
        )
        response = self.client.post(reverse("login"), {"phone": "ybek", "password": "ybek"})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("admin_panel"))

    def test_registration_post_creates_user_and_starts_session(self):
        response = self.client.post(reverse("register"), {
            "first_name": "New Viewer",
            "phone": "+998 90 123 45 75",
            "password1": "test-password",
            "password2": "test-password",
        })

        self.assertRedirects(response, reverse("home"))
        user = User.objects.get(phone="+998901234575")
        self.assertTrue(user.check_password("test-password"))
        self.assertEqual(self.client.session["_auth_user_id"], str(user.pk))

    def test_logout_post_ends_session(self):
        user = User.objects.create_user(phone="+998901234576", password="q", first_name="Viewer")
        self.client.force_login(user)

        response = self.client.post(reverse("logout"))

        self.assertRedirects(response, reverse("login"))
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_profile_and_register_pages_render(self):
        self.assertEqual(self.client.get(reverse("register")).status_code, 200)
        user = User.objects.create_user(phone="+998901234570", password="q", first_name="Viewer")
        self.client.force_login(user)
        profile_response = self.client.get(reverse("profile"))
        self.assertEqual(profile_response.status_code, 200)
        self.assertContains(profile_response, "data-open-logout")
        self.assertContains(profile_response, "data-close-logout")
        self.assertContains(profile_response, "Ha, chiqish")
        self.assertEqual(self.client.get(reverse("password_change")).status_code, 200)

    def test_staff_dashboard_and_django_admin_user_form_render(self):
        staff = User.objects.create_user(phone="+998901234571", password="q", first_name="Staff", is_staff=True, is_superuser=True)
        self.client.force_login(staff)
        self.assertEqual(self.client.get(reverse("admin_panel")).status_code, 200)
        self.assertEqual(self.client.get(reverse("admin_user_add")).status_code, 200)
        self.assertEqual(self.client.get(reverse("admin_category_add")).status_code, 200)
        self.assertEqual(self.client.get(reverse("video_create")).status_code, 200)
        self.assertEqual(self.client.get(reverse("admin:accounts_user_add")).status_code, 200)

    def test_staff_admin_cannot_edit_or_delete_superuser(self):
        staff = User.objects.create_user(phone="+998901234573", password="q", first_name="Staff", is_staff=True)
        owner = User.objects.create_superuser(phone="+998901234574", password="q", first_name="Owner")
        self.client.force_login(staff)
        edit_response = self.client.get(reverse("admin_user_edit", args=[owner.pk]))
        self.assertEqual(edit_response.status_code, 302)
        delete_response = self.client.post(reverse("admin_user_delete", args=[owner.pk]))
        self.assertEqual(delete_response.status_code, 302)
        self.assertTrue(User.objects.filter(pk=owner.pk, is_superuser=True).exists())