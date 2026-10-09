"""Forms for signup and room creation."""
from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User


class SignupForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ("username", "email", "password1", "password2")


class DirectRoomForm(forms.Form):
    """Start a one-to-one chat by entering the other person's username."""

    username = forms.CharField(max_length=150, label="Chat with (username)")


class GroupRoomForm(forms.Form):
    """Create a group room: a name plus comma-separated member usernames."""

    name = forms.CharField(max_length=255, label="Room name")
    members = forms.CharField(
        required=False,
        label="Members (comma-separated usernames)",
        help_text="You are added automatically.",
    )
