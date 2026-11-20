from django import forms
from pathlib import Path

from .models import Category, Video


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ["name"]
        labels = {"name": "Kategoriya nomi"}


class VideoForm(forms.ModelForm):
    class Meta:
        model = Video
        fields = ["title", "category", "description", "thumbnail", "file"]
        labels = {
            "title": "Video nomi",
            "category": "Kategoriya",
            "description": "Tavsif",
            "thumbnail": "Muqova rasmi",
            "file": "Video fayli",
        }
        widgets = {"description": forms.Textarea(attrs={"rows": 5})}

    def clean_file(self):
        video_file = self.cleaned_data.get("file")
        if video_file:
            extension = Path(video_file.name).suffix.lower()
            if extension not in {".mp4", ".webm", ".mov", ".m4v", ".ogv"}:
                raise forms.ValidationError("MP4, WebM, MOV, M4V yoki OGV formatidagi video yuklang.")
            if video_file.size > 2 * 1024 * 1024 * 1024:
                raise forms.ValidationError("Video hajmi 2 GB dan oshmasligi kerak.")
        return video_file

    def clean_thumbnail(self):
        thumbnail = self.cleaned_data.get("thumbnail")
        if thumbnail and thumbnail.size > 20 * 1024 * 1024:
            raise forms.ValidationError("Muqova rasmi 20 MB dan oshmasligi kerak.")
        return thumbnail