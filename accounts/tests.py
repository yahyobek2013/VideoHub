from io import StringIO
import sqlite3
import tempfile
from pathlib import Path
from unittest.mock import patch

from django.test import TestCase, override_settings
from django.urls import reverse
from django.core.management import call_command

from .forms import RegistrationForm
from .models import User


class AccountFlowTests(TestCase):
    def test_sqlite_diagnostics_requires_token_and_is_read_only(self):
        with tempfile.TemporaryDirectory() as directory:
            database_path = Path(directory) / "diagnostics.sqlite3"
            connection = sqlite3.connect(database_path)
            connection.execute(
                "CREATE TABLE accounts_user (id INTEGER, password TEXT, phone TEXT, first_name TEXT)"
            )
            connection.execute(
                "CREATE TABLE django_migrations (app TEXT, name TEXT)"
            )
            connection.execute(
                "INSERT INTO accounts_user (id, password, phone, first_name) VALUES (?, ?, ?, ?)",
                (1, "dummy-password-value", "+998901234581", "private-alias"),
            )
            connection.execute(
                "INSERT INTO django_migrations (app, name) VALUES (?, ?)",
                ("accounts", "0001_initial"),
            )
            connection.commit()
            connection.close()

            with override_settings(DATABASES={
                "default": {
                    "ENGINE": "django.db.backends.sqlite3",
                    "NAME": str(database_path),
                }
            }), patch.dict("os.environ", {"VH_SQLITE_DIAGNOSTICS_TOKEN": "diagnostic-test-token"}):
                url = reverse("sqlite_diagnostics")
                get_response = self.client.get(url)
                self.assertEqual(get_response.status_code, 200)
                self.assertContains(get_response, 'name="token"')
                self.assertNotContains(get_response, "accounts_user")

                invalid_response = self.client.post(url, {"token": "wrong-token"})
                self.assertEqual(invalid_response.status_code, 403)
                self.assertNotIn(b"accounts_user", invalid_response.content)

                response = self.client.post(url, {"token": "diagnostic-test-token"})

            self.assertEqual(response.status_code, 200)
            self.assertContains(response, "accounts_user")
            self.assertContains(response, "login_name")
            self.assertContains(response, "0002_user_login_name")
            self.assertIn("login_name", response.context["missing_user_columns"])
            migrations = {
                migration["name"]: migration["applied"]
                for migration in response.context["account_migrations"]
            }
            self.assertFalse(migrations["0002_user_login_name"])
            self.assertNotContains(response, "diagnostic-test-token")
            self.assertNotContains(response, "dummy-password-value")
            self.assertNotContains(response, "private-alias")
            self.assertNotContains(response, "+998901234581")
            self.assertNotContains(response, "SECRET_KEY")

            connection = sqlite3.connect(f"{database_path.as_uri()}?mode=ro", uri=True)
            migrations = connection.execute(
                "SELECT name FROM django_migrations WHERE app = ?", ("accounts",)
            ).fetchall()
            connection.close()
            self.assertEqual(migrations, [("0001_initial",)])

    def test_sqlite_diagnostics_is_disabled_without_token(self):
        with patch.dict("os.environ") as environment:
            environment.pop("VH_SQLITE_DIAGNOSTICS_TOKEN", None)
            with patch("accounts.views.sqlite3.connect") as connect:
                response = self.client.get(reverse("sqlite_diagnostics"))

        self.assertEqual(response.status_code, 503)
        connect.assert_not_called()

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

    def test_login_failure_logs_stage_without_credentials(self):
        self.client.raise_request_exception = False
        with patch("accounts.views.authenticate", side_effect=RuntimeError("test-only failure")):
            with self.assertLogs("accounts.auth", level="ERROR") as captured:
                response = self.client.post(reverse("login"), {
                    "phone": "+998901234577",
                    "password": "login-secret-test-value",
                })

        self.assertEqual(response.status_code, 500)
        log_output = "\n".join(captured.output)
        self.assertIn("flow=login stage=authenticate exception=RuntimeError", log_output)
        self.assertNotIn("login-secret-test-value", log_output)
        self.assertNotIn("+998901234577", log_output)

    def test_registration_failure_logs_stage_without_credentials(self):
        self.client.raise_request_exception = False
        with patch("accounts.forms.RegistrationForm.save", side_effect=RuntimeError("test-only failure")):
            with self.assertLogs("accounts.auth", level="ERROR") as captured:
                response = self.client.post(reverse("register"), {
                    "first_name": "Test User",
                    "phone": "+998901234578",
                    "password1": "register-secret-test-value",
                    "password2": "register-secret-test-value",
                })

        self.assertEqual(response.status_code, 500)
        log_output = "\n".join(captured.output)
        self.assertIn("flow=register stage=save_user exception=RuntimeError", log_output)
        self.assertNotIn("register-secret-test-value", log_output)
        self.assertNotIn("+998901234578", log_output)

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