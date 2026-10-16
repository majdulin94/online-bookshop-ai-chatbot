from django.views.decorators.http import require_POST
from django.conf import settings
from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, get_user_model
from django.contrib.auth.decorators import login_required
from .forms import RegisterForm, UserEditForm, ProfileEditForm
from .models import Profile
from chatbot.models import ChatSession
from .tokens import account_activation_token
from django.contrib.sites.shortcuts import get_current_site
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes
from django.template.loader import render_to_string
from django.core.mail import send_mail
from django.http import HttpRequest

def register_view(request: HttpRequest):
    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.is_active = False
            user.save()

            current_site = get_current_site(request)
            domain = request.get_host()
            protocol = 'https' if request.is_secure() else 'http'

            subject = "Aktiviere deinen Account"
            message = render_to_string("accounts/account_activation_email.html", {
                "user": user,
                "domain": domain,
                "uid": urlsafe_base64_encode(force_bytes(user.pk)),
                "token": account_activation_token.make_token(user),
                "protocol": protocol,
            })
            send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [user.email])

            return render(request, "accounts/registration_pending.html")
    else:
        form = RegisterForm()
    return render(request, "accounts/register.html", {"form": form})


@login_required
def profile(request):
    user = request.user
    profile = getattr(user, 'profile', None)
    return render(request, "accounts/profile.html", {"profile": profile})


@login_required
def edit_profile(request):
    profile, created = Profile.objects.get_or_create(user=request.user)

    if request.method == "POST":
        user_form = UserEditForm(request.POST, instance=request.user, user=request.user)
        profile_form = ProfileEditForm(request.POST, request.FILES, instance=profile)

        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            return redirect("profile")
    else:
        user_form = UserEditForm(instance=request.user, user=request.user)
        profile_form = ProfileEditForm(instance=profile)

    return render(request, "accounts/edit_profile.html", {
        "user_form": user_form,
        "profile_form": profile_form,
    })


@require_POST
def logout_view(request):
    if request.user.is_authenticated:
        active_sessions = ChatSession.objects.filter(user=request.user, status="active")
        for session in active_sessions:
            session.mark_expired()
    logout(request)
    return redirect("home")


def activate(request, uidb64, token):
    User = get_user_model()
    try:
        uid = urlsafe_base64_decode(uidb64).decode()
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, User.DoesNotExist):
        user = None

    if user and account_activation_token.check_token(user, token):
        user.is_active = True
        user.save()
        return render(request, "accounts/activation_success.html")
    else:
        return render(request, "accounts/activation_invalid.html")
