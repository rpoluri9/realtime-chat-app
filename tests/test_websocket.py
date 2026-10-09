"""Tests: real WebSocket behavior with channels' WebsocketCommunicator.

The whole test runs in ONE event loop (pytest-asyncio auto mode), which is
required for the communicator to work. Uses the in-memory channel layer,
so no Redis is needed.
"""
import pytest
from channels.db import database_sync_to_async
from channels.testing import WebsocketCommunicator
from django.contrib.auth.models import User

from chat.models import ChatRoom, Message, Token
from config.asgi import application


@database_sync_to_async
def create_user(username):
    user = User.objects.create_user(username=username, password="pw")
    token = Token.objects.create(user=user)
    return user.id, token.key


@database_sync_to_async
def create_room(name, member_ids):
    room = ChatRoom.objects.create(name=name, is_group=True)
    room.members.add(*member_ids)
    return room.id


@database_sync_to_async
def message_exists(room_id, text):
    return Message.objects.filter(room_id=room_id, text=text).exists()


async def connect(room_id, token_key):
    communicator = WebsocketCommunicator(
        application, f"/ws/chat/{room_id}/?token={token_key}"
    )
    connected, _ = await communicator.connect()
    return communicator, connected


async def drain_welcome(communicator):
    """After connect the client gets: history, then its own presence notice."""
    history = await communicator.receive_json_from()
    assert history["type"] == "history"
    presence = await communicator.receive_json_from()
    assert presence["type"] == "presence"
    assert presence["online"] is True


@pytest.mark.django_db(transaction=True)
async def test_websocket_send_and_receive():
    user_id, token_key = await create_user("alice")
    room_id = await create_room("General", [user_id])

    communicator, connected = await connect(room_id, token_key)
    assert connected
    await drain_welcome(communicator)

    await communicator.send_json_to({"type": "message", "text": "Hello WebSocket"})
    received = await communicator.receive_json_from()
    assert received["type"] == "message"
    assert received["text"] == "Hello WebSocket"
    assert received["user"] == "alice"

    # The message was saved to the database.
    assert await message_exists(room_id, "Hello WebSocket")

    await communicator.disconnect()


@pytest.mark.django_db(transaction=True)
async def test_message_broadcast_reaches_other_member():
    alice_id, alice_token = await create_user("alice")
    bob_id, bob_token = await create_user("bob")
    room_id = await create_room("General", [alice_id, bob_id])

    comm_alice, connected_a = await connect(room_id, alice_token)
    comm_bob, connected_b = await connect(room_id, bob_token)
    assert connected_a and connected_b
    await drain_welcome(comm_alice)
    await drain_welcome(comm_bob)
    # Bob's join announcement also arrives at Alice; skip it.
    join_notice = await comm_alice.receive_json_from()
    assert join_notice["type"] == "presence"

    await comm_alice.send_json_to({"type": "message", "text": "hi bob"})

    got_alice = await comm_alice.receive_json_from()
    got_bob = await comm_bob.receive_json_from()
    assert got_alice["text"] == "hi bob"
    assert got_bob["text"] == "hi bob"
    assert got_bob["user"] == "alice"

    await comm_alice.disconnect()
    await comm_bob.disconnect()


@pytest.mark.django_db(transaction=True)
async def test_typing_indicator_is_forwarded():
    user_id, token_key = await create_user("alice")
    room_id = await create_room("General", [user_id])

    communicator, connected = await connect(room_id, token_key)
    assert connected
    await drain_welcome(communicator)

    await communicator.send_json_to({"type": "typing"})
    received = await communicator.receive_json_from()
    assert received == {"type": "typing", "user": "alice"}

    await communicator.disconnect()


@pytest.mark.django_db(transaction=True)
async def test_connection_rejected_without_token():
    user_id, _ = await create_user("alice")
    room_id = await create_room("General", [user_id])

    communicator = WebsocketCommunicator(application, f"/ws/chat/{room_id}/")
    connected, _ = await communicator.connect()
    assert not connected


@pytest.mark.django_db(transaction=True)
async def test_connection_rejected_for_non_member():
    alice_id, _ = await create_user("alice")
    _, bob_token = await create_user("bob")
    room_id = await create_room("Secret", [alice_id])  # bob is NOT a member

    communicator, connected = await connect(room_id, bob_token)
    assert not connected
