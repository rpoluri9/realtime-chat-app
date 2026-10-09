"""Data model: rooms, messages, and WebSocket auth tokens."""
import secrets

from django.contrib.auth.models import User
from django.db import models


class ChatRoom(models.Model):
    """A conversation: either one-to-one (is_group=False) or a group room."""

    name = models.CharField(max_length=255)
    is_group = models.BooleanField(default=False)
    members = models.ManyToManyField(User, related_name="chat_rooms")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Message(models.Model):
    """One chat message, stored permanently so history survives restarts."""

    room = models.ForeignKey(
        ChatRoom, on_delete=models.CASCADE, related_name="messages"
    )
    sender = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="sent_messages"
    )
    text = models.TextField(blank=True)
    attachment = models.FileField(upload_to="attachments/", blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["timestamp"]

    def __str__(self):
        return f"{self.sender.username}: {self.text[:40]}"


class Token(models.Model):
    """Simple token used to authenticate WebSocket connections.

    The browser JS opens ws://...?token=<key>; the ASGI middleware
    turns the key back into a user.
    """

    key = models.CharField(max_length=40, primary_key=True)
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="ws_token"
    )
    created = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.key:
            self.key = secrets.token_hex(20)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"token for {self.user.username}"
