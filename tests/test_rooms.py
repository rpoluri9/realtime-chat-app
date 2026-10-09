"""Tests: room creation, membership, message persistence."""
import pytest
from django.contrib.auth.models import User

from chat.models import ChatRoom, Message
from chat.views import get_or_create_direct_room


@pytest.mark.django_db
def test_create_group_room(client):
    alice = User.objects.create_user(username="alice", password="pw")
    bob = User.objects.create_user(username="bob", password="pw")
    client.force_login(alice)
    res = client.post(
        "/rooms/",
        {"create_group": "1", "name": "Team", "members": "bob, nobody"},
    )
    assert res.status_code == 302
    room = ChatRoom.objects.get(name="Team")
    assert room.is_group
    assert set(room.members.all()) == {alice, bob}


@pytest.mark.django_db
def test_create_direct_room(client):
    alice = User.objects.create_user(username="alice", password="pw")
    bob = User.objects.create_user(username="bob", password="pw")
    client.force_login(alice)
    res = client.post("/rooms/", {"create_direct": "1", "username": "bob"})
    assert res.status_code == 302
    room = ChatRoom.objects.get()
    assert not room.is_group
    assert set(room.members.all()) == {alice, bob}


@pytest.mark.django_db
def test_direct_room_is_reused():
    alice = User.objects.create_user(username="alice", password="pw")
    bob = User.objects.create_user(username="bob", password="pw")
    room1 = get_or_create_direct_room(alice, bob)
    room2 = get_or_create_direct_room(bob, alice)
    assert room1.id == room2.id
    assert ChatRoom.objects.count() == 1


@pytest.mark.django_db
def test_message_history_is_persisted():
    alice = User.objects.create_user(username="alice", password="pw")
    room = ChatRoom.objects.create(name="General", is_group=True)
    room.members.add(alice)
    Message.objects.create(room=room, sender=alice, text="first")
    Message.objects.create(room=room, sender=alice, text="second")
    texts = list(room.messages.values_list("text", flat=True))
    assert texts == ["first", "second"]  # ordered by timestamp


@pytest.mark.django_db
def test_non_member_cannot_open_room(client):
    alice = User.objects.create_user(username="alice", password="pw")
    bob = User.objects.create_user(username="bob", password="pw")
    room = ChatRoom.objects.create(name="Private", is_group=True)
    room.members.add(alice)
    client.force_login(bob)
    res = client.get(f"/rooms/{room.id}/")
    assert res.status_code == 404


@pytest.mark.django_db
def test_file_upload_creates_message(client, tmp_path):
    from django.core.files.uploadedfile import SimpleUploadedFile

    alice = User.objects.create_user(username="alice", password="pw")
    room = ChatRoom.objects.create(name="Files", is_group=True)
    room.members.add(alice)
    client.force_login(alice)
    uploaded = SimpleUploadedFile("note.txt", b"hello file")
    res = client.post(f"/rooms/{room.id}/upload/", {"file": uploaded})
    assert res.status_code == 200
    assert res.json()["ok"] is True
    message = Message.objects.get(room=room)
    assert message.attachment.name.startswith("attachments/")
