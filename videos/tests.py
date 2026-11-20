from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from accounts.models import User

from .models import Category, SavedVideo, Video, VideoLike, VideoReaction
from .forms import VideoForm


class VideoInteractionTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(phone="+998901112233", password="q", first_name="Viewer")
        self.category = Category.objects.create(name="Sayohat")
        self.video = Video.objects.create(
            title="Tog‘lar",
            description="Tabiat manzaralari",
            category=self.category,
            file=SimpleUploadedFile("clip.mp4", b"test video bytes", content_type="video/mp4"),
        )
        self.client.force_login(self.user)

    def test_video_detail_increments_view_count(self):
        response = self.client.get(reverse("video_detail", args=[self.video.slug]))
        self.assertEqual(response.status_code, 200)
        self.video.refresh_from_db()
        self.assertEqual(self.video.views, 1)

    def test_home_lists_video_and_interaction_totals(self):
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.video.title)
        self.assertContains(response, "0 like")
        self.assertContains(response, "0 reaksiya")

    def test_like_and_saved_video_toggle_without_duplicates(self):
        url = reverse("toggle_like", args=[self.video.pk])
        self.assertEqual(self.client.post(url).json()["like_count"], 1)
        self.assertEqual(self.client.post(url).json()["like_count"], 0)
        self.assertEqual(VideoLike.objects.filter(user=self.user, video=self.video).count(), 0)

        save_url = reverse("toggle_saved", args=[self.video.pk])
        self.assertTrue(self.client.post(save_url).json()["saved"])
        self.assertFalse(self.client.post(save_url).json()["saved"])
        self.assertEqual(SavedVideo.objects.filter(user=self.user, video=self.video).count(), 0)

    def test_reaction_changes_and_can_be_removed(self):
        url = reverse("set_reaction", args=[self.video.pk])
        first = self.client.post(url, {"kind": VideoReaction.Kind.LOVE}).json()
        self.assertEqual(first["reaction"], VideoReaction.Kind.LOVE)
        changed = self.client.post(url, {"kind": VideoReaction.Kind.FIRE}).json()
        self.assertEqual(changed["reaction"], VideoReaction.Kind.FIRE)
        self.assertEqual(VideoReaction.objects.filter(user=self.user, video=self.video).count(), 1)
        removed = self.client.post(url, {"kind": VideoReaction.Kind.FIRE}).json()
        self.assertIsNone(removed["reaction"])
        self.assertEqual(VideoReaction.objects.filter(user=self.user, video=self.video).count(), 0)

    def test_non_staff_cannot_open_video_management(self):
        response = self.client.get(reverse("video_create"))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Video.objects.count(), 1)

    def test_video_form_rejects_non_video_file_extensions(self):
        form = VideoForm(
            data={"title": "Invalid", "category": self.category.pk, "description": "Description"},
            files={"file": SimpleUploadedFile("payload.txt", b"not a video", content_type="text/plain")},
        )
        self.assertFalse(form.is_valid())
        self.assertIn("file", form.errors)