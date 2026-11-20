from django import forms
from django.contrib.auth.forms import PasswordChangeForm, UserCreationForm
from django.core.validators import RegexValidator

from .models import User, normalize_phone


phone_validator = RegexValidator(r"^\+?\d{7,15}$", "Telefon raqam 7 dan 15 tagacha raqamdan iborat bo‘lsin.")


class RegistrationForm(forms.ModelForm):
    first_name = forms.CharField(max_length=150, label="Ism")
    phone = forms.CharField(max_length=32, label="Telefon raqam")
    password1 = forms.CharField(widget=forms.PasswordInput, label="Parol")
    password2 = forms.CharField(widget=forms.PasswordInput, label="Parolni takrorlang")

    class Meta:
        model = User
        fields = ["first_name", "phone"]
        labels = {"first_name": "Ism"}

    def clean_phone(self):
        phone = normalize_phone(self.cleaned_data["phone"])
        phone_validator(phone)
        if User.objects.filter(phone=phone).exists():
            raise forms.ValidationError("Bu telefon raqam avval ro‘yxatdan o‘tgan.")
        return phone

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get("password1") != cleaned_data.get("password2"):
            self.add_error("password2", "Parollar bir xil bo‘lishi kerak.")
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.phone = normalize_phone(user.phone)
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
        return user


class ProfileForm(forms.ModelForm):
    first_name = forms.CharField(max_length=150, label="Ism")
    phone = forms.CharField(max_length=32, label="Telefon raqam")

    class Meta:
        model = User
        fields = ["first_name", "phone"]
        labels = {"first_name": "Ism"}

    def clean_phone(self):
        phone = normalize_phone(self.cleaned_data["phone"])
        phone_validator(phone)
        if User.objects.exclude(pk=self.instance.pk).filter(phone=phone).exists():
            raise forms.ValidationError("Bu telefon raqam boshqa foydalanuvchiga tegishli.")
        return phone


class AdminUserForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput, label="Boshlang‘ich parol")
    phone = forms.CharField(max_length=32, label="Telefon raqam")

    class Meta:
        model = User
        fields = ["first_name", "phone", "login_name", "is_staff", "is_active"]
        labels = {"first_name": "Ism", "is_staff": "Admin huquqi", "is_active": "Faol"}

    def clean_phone(self):
        phone = normalize_phone(self.cleaned_data["phone"])
        phone_validator(phone)
        if User.objects.filter(phone=phone).exists():
            raise forms.ValidationError("Bu telefon raqam band.")
        return phone

    def clean_login_name(self):
        login_name = self.cleaned_data.get("login_name", "").strip()
        if login_name and User.objects.filter(login_name__iexact=login_name).exists():
            raise forms.ValidationError("Bu login band.")
        return login_name or None

    def save(self, commit=True):
        user = super().save(commit=False)
        user.phone = normalize_phone(user.phone)
        user.set_password(self.cleaned_data["password"])
        if commit:
            user.save()
        return user


class AdminUserEditForm(forms.ModelForm):
    phone = forms.CharField(max_length=32, label="Telefon raqam")

    def __init__(self, *args, can_manage_superuser=False, **kwargs):
        super().__init__(*args, **kwargs)
        if not can_manage_superuser:
            self.fields.pop("is_superuser", None)

    class Meta:
        model = User
        fields = ["first_name", "phone", "login_name", "is_active", "is_staff", "is_superuser"]
        labels = {
            "first_name": "Ism",
            "is_active": "Faol",
            "is_staff": "Admin paneliga kirish",
            "is_superuser": "To‘liq superuser huquqi",
        }

    def clean_phone(self):
        phone = normalize_phone(self.cleaned_data["phone"])
        phone_validator(phone)
        if User.objects.exclude(pk=self.instance.pk).filter(phone=phone).exists():
            raise forms.ValidationError("Bu telefon raqam boshqa foydalanuvchiga tegishli.")
        return phone

    def clean_login_name(self):
        login_name = self.cleaned_data.get("login_name", "").strip()
        if login_name and User.objects.exclude(pk=self.instance.pk).filter(login_name__iexact=login_name).exists():
            raise forms.ValidationError("Bu login band.")
        return login_name or None


class AdminUserCreationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("phone", "first_name", "login_name")

    def clean_phone(self):
        phone = normalize_phone(self.cleaned_data["phone"])
        phone_validator(phone)
        if User.objects.filter(phone=phone).exists():
            raise forms.ValidationError("Bu telefon raqam band.")
        return phone

    def clean_login_name(self):
        login_name = self.cleaned_data.get("login_name", "").strip()
        if login_name and User.objects.filter(login_name__iexact=login_name).exists():
            raise forms.ValidationError("Bu login band.")
        return login_name or None


class SimplePasswordChangeForm(PasswordChangeForm):
    pass