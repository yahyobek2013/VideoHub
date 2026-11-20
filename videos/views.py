import json

from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.paginator import Paginator
from django.db.models import Count, F, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .forms import VideoForm
from .models import Category, SavedVideo, Video, VideoLike, VideoReaction


def is_staff(user):
	return user.is_authenticated and user.is_staff


@login_required
def home(request):
	videos = Video.objects.select_related("category").annotate(
		like_total=Count("likes", distinct=True),
		reaction_total=Count("reactions", distinct=True),
	).order_by("-created_at", "-pk")
	query = request.GET.get("q", "").strip()
	category_slug = request.GET.get("category", "").strip()
	if query:
		videos = videos.filter(Q(title__icontains=query) | Q(description__icontains=query) | Q(category__name__icontains=query))
	if category_slug:
		videos = videos.filter(category__slug=category_slug)
	paginator = Paginator(videos, 18)
	page_obj = paginator.get_page(request.GET.get("page"))
	liked_ids = set(request.user.video_likes.values_list("video_id", flat=True))
	saved_ids = set(request.user.saved_videos.values_list("video_id", flat=True))
	return render(request, "home.html", {
		"videos": page_obj,
		"page_obj": page_obj,
		"categories": Category.objects.annotate(video_total=Count("videos")),
		"query": query,
		"selected_category": category_slug,
		"liked_ids": liked_ids,
		"saved_ids": saved_ids,
	})


@login_required
def video_detail(request, slug):
	video = get_object_or_404(Video.objects.select_related("category"), slug=slug)
	Video.objects.filter(pk=video.pk).update(views=F("views") + 1)
	video.refresh_from_db(fields=["views"])
	reactions = {item["kind"]: item["total"] for item in video.reactions.values("kind").annotate(total=Count("id"))}
	reaction_emojis = {"love": "❤️", "laugh": "😂", "wow": "😮", "sad": "😢", "fire": "🔥"}
	context = {
		"video": video,
		"liked": video.likes.filter(user=request.user).exists(),
		"saved": video.saved_by.filter(user=request.user).exists(),
		"user_reaction": video.reactions.filter(user=request.user).values_list("kind", flat=True).first(),
		"reaction_counts": reactions,
		"reaction_items": [
			{"kind": kind, "label": label.split(" ", 1)[1], "emoji": reaction_emojis[kind], "count": reactions.get(kind, 0), "selected": kind == video.reactions.filter(user=request.user).values_list("kind", flat=True).first()}
			for kind, label in VideoReaction.Kind.choices
		],
		"related_videos": Video.objects.filter(category=video.category).exclude(pk=video.pk).select_related("category")[:4],
	}
	return render(request, "video_detail.html", context)


def _interaction_response(video, user, message=""):
	reaction_counts = {kind: 0 for kind, _label in VideoReaction.Kind.choices}
	reaction_counts.update({
		row["kind"]: row["total"]
		for row in video.reactions.values("kind").annotate(total=Count("id"))
	})
	return JsonResponse({
		"ok": True,
		"message": message,
		"liked": video.likes.filter(user=user).exists(),
		"like_count": video.likes.count(),
		"saved": video.saved_by.filter(user=user).exists(),
		"reaction": video.reactions.filter(user=user).values_list("kind", flat=True).first(),
		"reaction_counts": reaction_counts,
		"reaction_total": video.reactions.count(),
	})


@login_required
@require_POST
def toggle_like(request, video_id):
	video = get_object_or_404(Video, pk=video_id)
	like, created = VideoLike.objects.get_or_create(user=request.user, video=video)
	if not created:
		like.delete()
	return _interaction_response(video, request.user)


@login_required
@require_POST
def set_reaction(request, video_id):
	video = get_object_or_404(Video, pk=video_id)
	kind = request.POST.get("kind", "")
	allowed = {value for value, _label in VideoReaction.Kind.choices}
	if kind not in allowed:
		return JsonResponse({"ok": False, "error": "Noma’lum reaksiya."}, status=400)
	reaction = VideoReaction.objects.filter(user=request.user, video=video).first()
	if reaction and reaction.kind == kind:
		reaction.delete()
	else:
		VideoReaction.objects.update_or_create(user=request.user, video=video, defaults={"kind": kind})
	return _interaction_response(video, request.user)


@login_required
@require_POST
def toggle_saved(request, video_id):
	video = get_object_or_404(Video, pk=video_id)
	saved, created = SavedVideo.objects.get_or_create(user=request.user, video=video)
	if not created:
		saved.delete()
	return _interaction_response(video, request.user)


@user_passes_test(is_staff, login_url="login")
def video_create(request):
	form = VideoForm(request.POST or None, request.FILES or None)
	if request.method == "POST" and form.is_valid():
		video = form.save()
		messages.success(request, "Video yuklandi.")
		return redirect("video_detail", slug=video.slug)
	return render(request, "video_form.html", {"form": form, "page_title": "Yangi video"})


@user_passes_test(is_staff, login_url="login")
def video_edit(request, video_id):
	video = get_object_or_404(Video, pk=video_id)
	form = VideoForm(request.POST or None, request.FILES or None, instance=video)
	if request.method == "POST" and form.is_valid():
		video = form.save()
		messages.success(request, "Video yangilandi.")
		return redirect("video_detail", slug=video.slug)
	return render(request, "video_form.html", {"form": form, "page_title": "Videoni tahrirlash", "video": video})


@require_POST
@user_passes_test(is_staff, login_url="login")
def video_delete(request, video_id):
	video = get_object_or_404(Video, pk=video_id)
	video.delete()
	messages.success(request, "Video o‘chirildi.")
	return redirect("admin_panel")
