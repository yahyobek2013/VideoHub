from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .forms import AdminUserCreationForm
from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
	add_form = AdminUserCreationForm
	ordering = ["phone"]
	list_display = ["phone", "login_name", "first_name", "is_staff", "is_active", "date_joined"]
	search_fields = ["phone", "login_name", "first_name"]
	fieldsets = (
		(None, {"fields": ("phone", "login_name", "password")}),
		("Shaxsiy ma’lumot", {"fields": ("first_name", "last_name")}),
		("Ruxsatlar", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
		("Sanalar", {"fields": ("last_login", "date_joined")}),
	)
	add_fieldsets = ((None, {"classes": ("wide",), "fields": ("phone", "login_name", "first_name", "password1", "password2", "is_staff", "is_superuser")}),)
