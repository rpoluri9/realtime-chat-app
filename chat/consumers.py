"""WebSocket consumer: the heart of the real-time chat.

One consumer instance handles one browser connection:
    connect    -> join the room's channel group, send history, announce presence
    receive    -> save chat messages, broadcast messages/typing to the group
    disconnect -> leave the group, announce presence
"""
from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer

from .models import ChatRoom, Message


class ChatConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        self.room_id = self.scope["url_route"]["kwargs"]["room_id"]
        self.user = self.scope.get("user")

        if not self.user or self.user.is_anonymous:
            await self.close()  # no token -> no entry
            return
        if not await self._is_member():
            await self.close()  # not a member of this room -> no entry
            return

        self.group_name = f"chat_{self.room_id}"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

        # Send recent history only to the newly connected client.
        history = await self._recent_messages(limit=50)
        await self.send_json({"type": "history", "messages": history})

        # Tell everyone in the room this user is now online.
        await self.channel_layer.group_send(
            self.group_name,
            {"type": "user_presence", "user": self.user.username, "online": True},
        )

    async def disconnect(self, close_code):
        if hasattr(self, "group_name"):
            await self.channel_layer.group_send(
                self.group_name,
                {"type": "user_presence", "user": self.user.username, "online": False},
            )
            await self.channel_layer.group_discard(
                self.group_name, self.channel_name
            )

    async def receive_json(self, content):
        msg_type = content.get("type")

        if msg_type == "message":
            text = (content.get("text") or "").strip()
            if not text:
                return
            message = await self._save_message(text)
            await self.channel_layer.group_send(
                self.group_name, {"type": "chat_message", **message}
            )
        elif msg_type == "typing":
            # Typing indicators are not stored, just forwarded.
            await self.channel_layer.group_send(
                self.group_name,
                {"type": "user_typing", "user": self.user.username},
            )

    # --- Handlers for events arriving from the channel layer ---

    async def chat_message(self, event):
        await self.send_json(
            {
                "type": "message",
                "id": event["id"],
                "user": event["user"],
                "text": event["text"],
                "attachment": event["attachment"],
                "timestamp": event["timestamp"],
            }
        )

    async def user_typing(self, event):
        await self.send_json(
            {"type": "typing", "user": event["user"]}
        )

    async def user_presence(self, event):
        await self.send_json(
            {"type": "presence", "user": event["user"], "online": event["online"]}
        )

    # --- Database helpers (run in a thread, since ORM calls are sync) ---

    @database_sync_to_async
    def _is_member(self):
        return ChatRoom.objects.filter(
            id=self.room_id, members=self.user
        ).exists()

    @database_sync_to_async
    def _save_message(self, text):
        message = Message.objects.create(
            room_id=self.room_id, sender=self.user, text=text
        )
        return self._serialize(message)

    @database_sync_to_async
    def _recent_messages(self, limit=50):
        messages = (
            Message.objects.filter(room_id=self.room_id)
            .select_related("sender")
            .order_by("-timestamp")[:limit]
        )
        return [self._serialize(m) for m in reversed(messages)]

    def _serialize(self, message):
        return {
            "id": message.id,
            "user": message.sender.username,
            "text": message.text,
            "attachment": message.attachment.url if message.attachment else None,
            "timestamp": message.timestamp.isoformat(),
        }
