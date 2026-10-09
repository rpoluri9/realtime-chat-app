"""Admin registrations for the chat models."""
from django.contrib import admin

from .models import ChatRoom, Message, Token


@admin.register(ChatRoom)
class ChatRoomAdmin(admin.ModelAdmin):
    list_display = ("name", "is_group", "created_at")
    filter_horizontal = ("members",)


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ("room", "sender", "text", "timestamp")
    list_filter = ("room",)


@admin.register(Token)
class TokenAdmin(admin.ModelAdmin):
    list_display = ("user", "created")
