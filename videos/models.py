from django.conf import settings
from django.db import models
from django.utils.text import slugify


class Category(models.Model):
	name = models.CharField(max_length=80, unique=True, verbose_name="Nomi")
	slug = models.SlugField(max_length=100, unique=True, blank=True)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ["name"]
		verbose_name = "kategoriya"
		verbose_name_plural = "kategoriyalar"

	def save(self, *args, **kwargs):
		self.slug = slugify(self.name) or "category"
		original = self.slug
		suffix = 2
		while Category.objects.exclude(pk=self.pk).filter(slug=self.slug).exists():
			self.slug = f"{original}-{suffix}"
			suffix += 1
		super().save(*args, **kwargs)

	def __str__(self):
		return self.name


class Video(models.Model):
	title = models.CharField(max_length=180, verbose_name="Video nomi")
	slug = models.SlugField(max_length=200, unique=True, blank=True)
	description = models.TextField(verbose_name="Tavsif")
	category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="videos")
	thumbnail = models.ImageField(upload_to="thumbnails/", blank=True, verbose_name="Muqova rasmi")
	file = models.FileField(upload_to="videos/", verbose_name="Video fayli")
	views = models.PositiveBigIntegerField(default=0)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		ordering = ["-created_at"]
		verbose_name = "video"
		verbose_name_plural = "videolar"

	def save(self, *args, **kwargs):
		base_slug = slugify(self.title) or "video"
		self.slug = base_slug
		suffix = 2
		while Video.objects.exclude(pk=self.pk).filter(slug=self.slug).exists():
			self.slug = f"{base_slug}-{suffix}"
			suffix += 1
		super().save(*args, **kwargs)

	@property
	def like_count(self):
		return self.likes.count()

	@property
	def reaction_count(self):
		return self.reactions.count()

	def __str__(self):
		return self.title


class VideoLike(models.Model):
	user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="video_likes")
	video = models.ForeignKey(Video, on_delete=models.CASCADE, related_name="likes")
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		constraints = [models.UniqueConstraint(fields=["user", "video"], name="unique_video_like")]
		ordering = ["-created_at"]


class VideoReaction(models.Model):
	class Kind(models.TextChoices):
		LOVE = "love", "❤️ Love"
		LAUGH = "laugh", "😂 Kulgi"
		WOW = "wow", "😮 Hayrat"
		SAD = "sad", "😢 Xafa"
		FIRE = "fire", "🔥 Zo‘r"

	user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="video_reactions")
	video = models.ForeignKey(Video, on_delete=models.CASCADE, related_name="reactions")
	kind = models.CharField(max_length=12, choices=Kind.choices)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		constraints = [models.UniqueConstraint(fields=["user", "video"], name="unique_video_reaction")]
		ordering = ["-updated_at"]


class SavedVideo(models.Model):
	user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="saved_videos")
	video = models.ForeignKey(Video, on_delete=models.CASCADE, related_name="saved_by")
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		constraints = [models.UniqueConstraint(fields=["user", "video"], name="unique_saved_video")]
		ordering = ["-created_at"]
