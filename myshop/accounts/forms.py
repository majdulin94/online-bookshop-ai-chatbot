from django import forms
from django.contrib.auth.models import User
from .models import Profile
from django.contrib.auth.forms import UserCreationForm
from django.forms.widgets import ClearableFileInput
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError

class RegisterForm(UserCreationForm):
    email = forms.EmailField()

    class Meta:
        model = User
        fields = ["username", "email", "password1", "password2"]

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("This email is already in use.")
        return email

class UserEditForm(forms.ModelForm):
    password1 = forms.CharField(
        label="New password",
        required=False,
        widget=forms.PasswordInput,
    )
    password2 = forms.CharField(
        label="Confirm new password",
        required=False,
        widget=forms.PasswordInput,
    )

    class Meta:
        model = User
        fields = ["username", "first_name", "last_name", "email"]

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)  # <- richtig: pop entfernt es aus kwargs
        super().__init__(*args, **kwargs)     # <- jetzt kein Fehler mehr

    def clean_username(self):
        username = self.cleaned_data.get('username')
        # Andere Benutzer mit gleichem Namen
        qs = User.objects.filter(username=username)
        if self.user:
            qs = qs.exclude(pk=self.user.pk)  # Eigenen Eintrag ignorieren
        if qs.exists():
            raise forms.ValidationError("This username is already taken")
        return username

    def clean_email(self):
        email = self.cleaned_data.get('email')
        qs = User.objects.filter(email=email)
        if self.user:
            qs = qs.exclude(pk=self.user.pk)
        if qs.exists():
            raise forms.ValidationError("This email address is already in use")
        return email

    def clean(self):
        cleaned_data = super().clean()
        pw1 = cleaned_data.get("password1")
        pw2 = cleaned_data.get("password2")

        if pw1 or pw2:
            if pw1 != pw2:
                raise forms.ValidationError("The passwords do not match")
            try:
                validate_password(pw1, user=self.user)
            except DjangoValidationError as e:
                raise forms.ValidationError(e.messages)

    def save(self, commit=True):
        user = super().save(commit=False)
        password = self.cleaned_data.get("password1")
        if password:
            user.set_password(password)
        if commit:
            user.save()
        return user


class CustomClearableFileInput(ClearableFileInput):
    template_name = 'widgets/custom_clearable_file_input.html'

class ProfileEditForm(forms.ModelForm):
    profile_picture = forms.ImageField(
        required=False,
        widget=CustomClearableFileInput(attrs={'class': 'form-control'}),
        help_text='',  # Hilfetext optional ausblenden
    )

    birthday = forms.DateField(
        required=False,
        widget=forms.DateInput(
            attrs={
                'type': 'date',  # HTML5 Datumsauswahl
                'class': 'form-control',
            }
        ),
        input_formats=['%Y-%m-%d'],  # Optional: passend zum HTML5 Format
    )

    class Meta:
        model = Profile
        fields = ["profile_picture", "birthday"]
