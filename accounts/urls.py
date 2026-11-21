from django.urls import path

from videos import views as video_views

from . import views


urlpatterns = [
	path("", views.splash_view, name="splash"),
	path("home/", video_views.home, name="home"),
	path("login/", views.login_view, name="login"),
	path("register/", views.register_view, name="register"),
	path("logout/", views.logout_view, name="logout"),
	path("profile/", views.profile_view, name="profile"),
	path("profile/password/", views.password_change_view, name="password_change"),
	path("profile/videos/<str:list_type>/", views.personal_videos, name="personal_videos"),
	path("info/", views.info_view, name="info"),
	path("dashboard/admin/", views.admin_panel, name="admin_panel"),
	path("dashboard/admin/diagnostics/sqlite/", views.sqlite_diagnostics, name="sqlite_diagnostics"),
	path("dashboard/admin/users/add/", views.admin_user_add, name="admin_user_add"),
	path("dashboard/admin/users/<int:user_id>/edit/", views.admin_user_edit, name="admin_user_edit"),
	path("dashboard/admin/users/<int:user_id>/delete/", views.admin_user_delete, name="admin_user_delete"),
	path("dashboard/admin/categories/add/", views.admin_category_add, name="admin_category_add"),
	path("dashboard/admin/categories/<int:category_id>/edit/", views.admin_category_edit, name="admin_category_edit"),
	path("dashboard/admin/categories/<int:category_id>/delete/", views.admin_category_delete, name="admin_category_delete"),
]
