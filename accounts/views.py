import logging
import sqlite3
from pathlib import Path

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.exceptions import PermissionDenied
from django.conf import settings
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_POST

from videos.forms import CategoryForm
from videos.models import Category, SavedVideo, Video, VideoLike, VideoReaction

from .forms import AdminUserEditForm, AdminUserForm, ProfileForm, RegistrationForm, SimplePasswordChangeForm
from .models import User, normalize_phone


auth_logger = logging.getLogger("accounts.auth")


def login_view(request):
	if request.user.is_authenticated:
		return redirect("admin_panel" if request.user.is_staff else "home")
	if request.method == "POST":
		stage = "read_identifier"
		try:
			identifier = request.POST.get("phone", "").strip()
			phone = normalize_phone(identifier)
			if not phone.replace("+", "").isdigit():
				stage = "lookup_login_name"
				phone = User.objects.filter(login_name__iexact=identifier, is_active=True).values_list("phone", flat=True).first() or ""
			stage = "authenticate"
			user = authenticate(request, phone=phone, password=request.POST.get("password", ""))
			if user is not None:
				stage = "create_session"
				login(request, user)
				return redirect("admin_panel" if user.is_staff else "home")
			messages.error(request, "Telefon raqam yoki parol noto‘g‘ri.")
		except Exception as exc:
			auth_logger.error("Authentication POST failed: flow=login stage=%s exception=%s", stage, type(exc).__name__)
			raise
	return render(request, "login.html")


def splash_view(request):
	if request.user.is_authenticated:
		return redirect("home")
	return render(request, "splash.html")


def register_view(request):
	if request.user.is_authenticated:
		return redirect("home")
	form = RegistrationForm(request.POST or None)
	if request.method == "POST":
		stage = "validate_registration"
		try:
			if form.is_valid():
				stage = "save_user"
				user = form.save()
				stage = "create_session"
				login(request, user, backend="django.contrib.auth.backends.ModelBackend")
				messages.success(request, "VideoHub’ga xush kelibsiz!")
				return redirect("home")
		except Exception as exc:
			auth_logger.error("Authentication POST failed: flow=register stage=%s exception=%s", stage, type(exc).__name__)
			raise
	return render(request, "register.html", {"form": form})


@require_POST
def logout_view(request):
	logout(request)
	return redirect("login")


@login_required
def profile_view(request):
	form = ProfileForm(request.POST or None, instance=request.user)
	if request.method == "POST" and form.is_valid():
		form.save()
		messages.success(request, "Profil ma’lumotlari saqlandi.")
		return redirect("profile")
	context = {
		"form": form,
		"saved_count": request.user.saved_videos.count(),
		"liked_count": request.user.video_likes.count(),
		"reaction_count": request.user.video_reactions.count(),
	}
	return render(request, "profile.html", context)


@login_required
def password_change_view(request):
	form = SimplePasswordChangeForm(request.user, request.POST or None)
	if request.method == "POST" and form.is_valid():
		user = form.save()
		update_session_auth_hash(request, user)
		messages.success(request, "Parol muvaffaqiyatli o‘zgartirildi.")
		return redirect("profile")
	return render(request, "password_change.html", {"form": form})


@login_required
def personal_videos(request, list_type):
	if list_type == "saved":
		videos = Video.objects.filter(saved_by__user=request.user)
		title = "Saqlangan videolar"
	elif list_type == "liked":
		videos = Video.objects.filter(likes__user=request.user)
		title = "Like bosilgan videolar"
	else:
		videos = Video.objects.filter(reactions__user=request.user)
		title = "Reaksiya bildirilgan videolar"
	videos = videos.select_related("category").annotate(like_total=Count("likes", distinct=True), reaction_total=Count("reactions", distinct=True))
	return render(request, "home.html", {
		"videos": videos,
		"categories": Category.objects.all(),
		"active_list": title,
		"page_title": title,
		"liked_ids": set(request.user.video_likes.values_list("video_id", flat=True)),
		"saved_ids": set(request.user.saved_videos.values_list("video_id", flat=True)),
	})


def info_view(request):
	return render(request, "info.html")


def is_staff(user):
	return user.is_authenticated and user.is_staff


@user_passes_test(is_staff, login_url="login")
def admin_panel(request):
	context = {
		"users": User.objects.order_by("-date_joined"),
		"videos": Video.objects.select_related("category").annotate(like_total=Count("likes", distinct=True), reaction_total=Count("reactions", distinct=True))[:100],
		"categories": Category.objects.annotate(video_total=Count("videos")),
		"user_count": User.objects.count(),
		"video_count": Video.objects.count(),
		"view_count": sum(Video.objects.values_list("views", flat=True)),
		"like_count": VideoLike.objects.count(),
		"reaction_count": VideoReaction.objects.count(),
		"likes": VideoLike.objects.select_related("user", "video").order_by("-created_at")[:100],
		"reactions": VideoReaction.objects.select_related("user", "video").order_by("-updated_at")[:100],
	}
	return render(request, "admin_panel.html", context)


@require_GET
@login_required
def sqlite_diagnostics(request):
	if not request.user.is_active or not request.user.is_superuser:
		raise PermissionDenied

	database_path = Path(settings.DATABASES["default"]["NAME"])
	known_tables = {"accounts_user", "django_migrations"}
	expected_columns = {
		"id", "password", "last_login", "is_superuser", "first_name", "last_name",
		"email", "is_staff", "is_active", "date_joined", "phone", "login_name",
	}
	result = {
		"database_path": str(database_path),
		"database_exists": database_path.is_file(),
		"connection_error": None,
		"tables": {name: False for name in sorted(known_tables)},
		"missing_user_columns": sorted(expected_columns),
		"account_migrations": [],
	}

	try:
		connection = sqlite3.connect(f"{database_path.as_uri()}?mode=ro", uri=True, timeout=2)
		try:
			connection.execute("PRAGMA query_only = ON")
			tables = {
				row[0]
				for row in connection.execute(
					"SELECT name FROM sqlite_master WHERE type = ? AND name IN (?, ?)",
					("table", *sorted(known_tables)),
				)
			}
			result["tables"] = {name: name in tables for name in sorted(known_tables)}
			if "accounts_user" in tables:
				columns = {
					row[1]
					for row in connection.execute("PRAGMA table_info(accounts_user)")
				}
				result["missing_user_columns"] = sorted(expected_columns - columns)
			if "django_migrations" in tables:
				result["account_migrations"] = [
					row[0]
					for row in connection.execute(
						"SELECT name FROM django_migrations WHERE app = ? ORDER BY name",
						("accounts",),
					)
				]
		finally:
			connection.close()
	except (OSError, sqlite3.Error) as exc:
		result["connection_error"] = type(exc).__name__

	return render(request, "sqlite_diagnostics.html", result)


@user_passes_test(is_staff, login_url="login")
def admin_user_add(request):
	form = AdminUserForm(request.POST or None)
	if request.method == "POST" and form.is_valid():
		form.save()
		messages.success(request, "Foydalanuvchi yaratildi.")
		return redirect("admin_panel")
	return render(request, "admin_user_form.html", {"form": form, "page_title": "Foydalanuvchi qo‘shish"})


@user_passes_test(is_staff, login_url="login")
def admin_user_edit(request, user_id):
	target = get_object_or_404(User, pk=user_id)
	if target.is_superuser and not request.user.is_superuser:
		messages.error(request, "Superuser hisobini faqat superuser tahrirlashi mumkin.")
		return redirect("admin_panel")
	form = AdminUserEditForm(request.POST or None, instance=target, can_manage_superuser=request.user.is_superuser)
	if request.method == "POST" and form.is_valid():
		if target.pk == request.user.pk and not form.cleaned_data["is_staff"]:
			form.add_error("is_staff", "Joriy admin huquqini o‘zingiz olib tashlay olmaysiz.")
		elif target.is_superuser and User.objects.filter(is_superuser=True).count() == 1 and not form.cleaned_data["is_superuser"]:
			form.add_error("is_superuser", "Oxirgi superuser huquqini olib tashlab bo‘lmaydi.")
		else:
			form.save()
			messages.success(request, "Foydalanuvchi yangilandi.")
			return redirect("admin_panel")
	return render(request, "admin_user_form.html", {"form": form, "page_title": "Foydalanuvchini tahrirlash", "target": target})


@require_POST
@user_passes_test(is_staff, login_url="login")
def admin_user_delete(request, user_id):
	target = get_object_or_404(User, pk=user_id)
	if target.pk == request.user.pk:
		messages.error(request, "O‘zingizning akkauntingizni bu paneldan o‘chira olmaysiz.")
	elif target.is_superuser and not request.user.is_superuser:
		messages.error(request, "Superuser hisobini faqat superuser o‘chirishi mumkin.")
	elif target.is_superuser and User.objects.filter(is_superuser=True).count() <= 1:
		messages.error(request, "Oxirgi superuser akkauntini o‘chirib bo‘lmaydi.")
	else:
		target.delete()
		messages.success(request, "Foydalanuvchi o‘chirildi.")
	return redirect("admin_panel")


@user_passes_test(is_staff, login_url="login")
def admin_category_add(request):
	form = CategoryForm(request.POST or None)
	if request.method == "POST" and form.is_valid():
		form.save()
		messages.success(request, "Kategoriya yaratildi.")
		return redirect("admin_panel")
	return render(request, "category_form.html", {"form": form, "page_title": "Kategoriya qo‘shish"})


@user_passes_test(is_staff, login_url="login")
def admin_category_edit(request, category_id):
	category = get_object_or_404(Category, pk=category_id)
	form = CategoryForm(request.POST or None, instance=category)
	if request.method == "POST" and form.is_valid():
		form.save()
		messages.success(request, "Kategoriya yangilandi.")
		return redirect("admin_panel")
	return render(request, "category_form.html", {"form": form, "page_title": "Kategoriyani tahrirlash", "category": category})


@require_POST
@user_passes_test(is_staff, login_url="login")
def admin_category_delete(request, category_id):
	category = get_object_or_404(Category, pk=category_id)
	if category.videos.exists():
		messages.error(request, "Video biriktirilgan kategoriyani avval bo‘shating yoki videolarni boshqa kategoriyaga o‘tkazing.")
	else:
		category.delete()
		messages.success(request, "Kategoriya o‘chirildi.")
	return redirect("admin_panel")
