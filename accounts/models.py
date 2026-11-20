from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractUser
from django.db import models


def normalize_phone(value):
	return "".join(character for character in value.strip() if character not in " -()")


class UserManager(BaseUserManager):
	use_in_migrations = True

	def create_user(self, phone, password=None, **extra_fields):
		if not phone:
			raise ValueError("Telefon raqam kiritilishi shart")
		user = self.model(phone=normalize_phone(phone), **extra_fields)
		user.set_password(password)
		user.save(using=self._db)
		return user

	def create_superuser(self, phone, password=None, **extra_fields):
		extra_fields.setdefault("is_staff", True)
		extra_fields.setdefault("is_superuser", True)
		extra_fields.setdefault("is_active", True)
		if not extra_fields["is_staff"] or not extra_fields["is_superuser"]:
			raise ValueError("Superuser staff va superuser huquqiga ega bo‘lishi kerak")
		return self.create_user(phone, password, **extra_fields)


class User(AbstractUser):
	username = None
	phone = models.CharField(max_length=32, unique=True, verbose_name="Telefon raqam")
	login_name = models.CharField(max_length=64, unique=True, blank=True, null=True, verbose_name="Login")

	USERNAME_FIELD = "phone"
	REQUIRED_FIELDS = ["first_name"]

	objects = UserManager()

	class Meta:
		ordering = ["-date_joined"]
		verbose_name = "foydalanuvchi"
		verbose_name_plural = "foydalanuvchilar"

	def __str__(self):
		return self.get_full_name() or self.phone
