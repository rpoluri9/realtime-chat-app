"""HTTP views: auth, room list, chat page, and file uploads."""
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .forms import DirectRoomForm, GroupRoomForm, SignupForm
from .models import ChatRoom, Message, Token


def signup_view(request):
    if request.method == "POST":
        form = SignupForm(request.POST)
        if form.is_valid():
            user = form.save()
            Token.objects.create(user=user)
            login(request, user)
            return redirect("room_list")
    else:
        form = SignupForm()
    return render(request, "chat/signup.html", {"form": form})


@login_required
def room_list_view(request):
    rooms = request.user.chat_rooms.all().order_by("-created_at")
    direct_form = DirectRoomForm()
    group_form = GroupRoomForm()

    if request.method == "POST":
        if "create_direct" in request.POST:
            direct_form = DirectRoomForm(request.POST)
            if direct_form.is_valid():
                username = direct_form.cleaned_data["username"]
                try:
                    other = User.objects.get(username=username)
                except User.DoesNotExist:
                    messages.error(request, f"User '{username}' not found.")
                    other = None
                if other and other != request.user:
                    room = get_or_create_direct_room(request.user, other)
                    return redirect("room_detail", room_id=room.id)
        elif "create_group" in request.POST:
            group_form = GroupRoomForm(request.POST)
            if group_form.is_valid():
                room = ChatRoom.objects.create(
                    name=group_form.cleaned_data["name"], is_group=True
                )
                room.members.add(request.user)
                for username in group_form.cleaned_data["members"].split(","):
                    username = username.strip()
                    if username:
                        try:
                            room.members.add(User.objects.get(username=username))
                        except User.DoesNotExist:
                            messages.warning(
                                request, f"User '{username}' not found, skipped."
                            )
                return redirect("room_detail", room_id=room.id)

    return render(
        request,
        "chat/room_list.html",
        {"rooms": rooms, "direct_form": direct_form, "group_form": group_form},
    )


def get_or_create_direct_room(user_a, user_b):
    """Find the existing 1-1 room for two users, or create it."""
    for room in ChatRoom.objects.filter(is_group=False, members=user_a):
        member_ids = set(room.members.values_list("id", flat=True))
        if member_ids == {user_a.id, user_b.id}:
            return room
    room = ChatRoom.objects.create(name=f"{user_a.username} & {user_b.username}")
    room.members.add(user_a, user_b)
    return room


@login_required
def room_detail_view(request, room_id):
    room = get_object_or_404(ChatRoom, id=room_id, members=request.user)
    token, _ = Token.objects.get_or_create(user=request.user)
    return render(
        request, "chat/chat.html", {"room": room, "ws_token": token.key}
    )


@login_required
@require_POST
def upload_attachment_view(request, room_id):
    """Upload a file into a room: saved as a Message, then broadcast live."""
    room = get_object_or_404(ChatRoom, id=room_id, members=request.user)
    uploaded = request.FILES.get("file")
    if not uploaded:
        return JsonResponse({"error": "No file uploaded."}, status=400)

    message = Message.objects.create(
        room=room, sender=request.user, text=uploaded.name, attachment=uploaded
    )
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f"chat_{room.id}",
        {
            "type": "chat_message",
            "id": message.id,
            "user": request.user.username,
            "text": message.text,
            "attachment": message.attachment.url,
            "timestamp": message.timestamp.isoformat(),
        },
    )
    return JsonResponse({"ok": True, "url": message.attachment.url})
