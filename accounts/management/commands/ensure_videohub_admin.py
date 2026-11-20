import os

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from accounts.models import User, normalize_phone


class Command(BaseCommand):
	help = "Create or refresh the VideoHub deployment administrator."

	@transaction.atomic
	def handle(self, *args, **options):
		phone = normalize_phone(os.environ.get("VH_ADMIN_PHONE", "930804866"))
		login_name = os.environ.get("VH_ADMIN_LOGIN", "ybek").strip()
		password = os.environ.get("VH_ADMIN_PASSWORD", "")
		first_name = os.environ.get("VH_ADMIN_NAME", "Yahyobek Yaqubboyev").strip()

		if not phone or not login_name or not password or not first_name:
			raise CommandError("Admin telefon, login, parol va ism to‘ldirilishi shart; Render’da VH_ADMIN_PASSWORD secret’ini sozlang.")

		alias_owner = User.objects.filter(login_name__iexact=login_name).exclude(phone=phone).first()
		if alias_owner:
			raise CommandError(f"{login_name} login’i boshqa foydalanuvchiga biriktirilgan.")

		user, created = User.objects.get_or_create(
			phone=phone,
			defaults={
				"first_name": first_name,
				"login_name": login_name,
				"is_active": True,
				"is_staff": True,
				"is_superuser": True,
			},
		)
		user.first_name = first_name
		user.login_name = login_name
		user.is_active = True
		user.is_staff = True
		user.is_superuser = True
		user.set_password(password)
		user.save(update_fields=["first_name", "login_name", "is_active", "is_staff", "is_superuser", "password"])

		status = "created" if created else "updated"
		self.stdout.write(self.style.SUCCESS(f"VideoHub administrator {status}: {phone} ({login_name})"))