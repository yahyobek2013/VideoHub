from django.urls import path

from . import views


urlpatterns = [
	path("<slug:slug>/", views.video_detail, name="video_detail"),
	path("api/<int:video_id>/like/", views.toggle_like, name="toggle_like"),
	path("api/<int:video_id>/reaction/", views.set_reaction, name="set_reaction"),
	path("api/<int:video_id>/save/", views.toggle_saved, name="toggle_saved"),
	path("dashboard/new/", views.video_create, name="video_create"),
	path("dashboard/<int:video_id>/edit/", views.video_edit, name="video_edit"),
	path("dashboard/<int:video_id>/delete/", views.video_delete, name="video_delete"),
]
