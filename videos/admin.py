from django.contrib import admin

from .models import Category, SavedVideo, Video, VideoLike, VideoReaction


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
	list_display = ["name", "slug", "created_at"]
	search_fields = ["name"]
	prepopulated_fields = {"slug": ("name",)}


@admin.register(Video)
class VideoAdmin(admin.ModelAdmin):
	list_display = ["title", "category", "views", "created_at"]
	list_filter = ["category", "created_at"]
	search_fields = ["title", "description"]
	readonly_fields = ["views", "created_at", "updated_at"]


@admin.register(VideoLike)
class VideoLikeAdmin(admin.ModelAdmin):
	list_display = ["user", "video", "created_at"]
	list_filter = ["created_at"]
	search_fields = ["user__phone", "video__title"]


@admin.register(VideoReaction)
class VideoReactionAdmin(admin.ModelAdmin):
	list_display = ["user", "video", "kind", "updated_at"]
	list_filter = ["kind", "updated_at"]
	search_fields = ["user__phone", "video__title"]


@admin.register(SavedVideo)
class SavedVideoAdmin(admin.ModelAdmin):
	list_display = ["user", "video", "created_at"]
	search_fields = ["user__phone", "video__title"]
