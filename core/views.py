import base64
import json
from urllib import request
from django.conf import settings
from django.core.files.base import ContentFile
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_http_methods
from django.contrib.auth import login, logout, get_user_model
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.db import IntegrityError
from django.utils import timezone
from .utils import are_friends, get_friends, get_or_create_chat, update_streak
from .models import FriendRequest, Message, Chat
from . import forms


# Create your views here.
@require_http_methods(["GET", "POST"])
def register_view(request):
    if request.user.is_authenticated:
        return redirect("home")

    form = forms.RegisterForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user)
        return redirect("home")
    return render(request, "accounts/register.html", {"form": form})


@require_http_methods(["GET", "POST"])
def login_view(request):
    if request.user.is_authenticated:
        return redirect("home")

    form = forms.LoginForm(request, data=request.POST or None)
    if request.method == "POST" and form.is_valid():
        login(request, form.get_user())
        return redirect("home")
    return render(request, "accounts/login.html", {"form": form})


@login_required
def profile_view(request):
    spotlights = request.user.spotlights.all().order_by("-created_at")
    return render(request, "accounts/profile.html", {"spotlights": spotlights})


@login_required
@require_http_methods(["GET", "POST"])
def change_avatar_view(request):
    form = forms.ChangeAvatarForm(
        request.POST or None,
        request.FILES or None,
        instance=request.user,
    )
    if request.method == "POST" and form.is_valid():
        old_name = request.user.avatar.name if request.user.avatar else None
        form.save()
        defaults = ("snaps/default.jpg", "avatar/default.jpg")
        if (
            old_name
            and old_name not in defaults
            and old_name != request.user.avatar.name
        ):
            request.user.avatar.storage.delete(old_name)
        return redirect("profile")
    return render(request, "accounts/change-avatar.html", {"form": form})


@login_required
@require_http_methods(["GET", "POST"])
def edit_username_view(request):
    form = forms.EditUsernameForm(request.POST or None, instance=request.user)
    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect("profile")
    return render(request, "accounts/edit-username.html", {"form": form})


@require_http_methods(["POST"])
def logout_view(request):
    logout(request)
    return redirect("login")


@login_required
def home(request):
    friends = get_friends(request.user)
    locationform = forms.LocationForm()
    chat_list = []
    for friend in friends:
        chat = get_or_create_chat(request.user, friend)

        last_message = chat.messages.order_by("-created_at").first()
        if last_message is None:
            last_message_text = "say Hii"
        elif last_message.image:
            last_message_text = "new snap"
        else:
            last_message_text = last_message.text
        chat_list.append((friend, chat, last_message_text, last_message))

    chat_list.sort(key=lambda row: row[1].last_message, reverse=True)
    return render(
        request, "pages/chat.html", {"chats": chat_list, "locationform": locationform}
    )


@login_required
def chat_details_view(request, id):
    chat = get_object_or_404(Chat, pk=id)
    messages = chat.messages.all().order_by("created_at")
    update_streak(chat)

    friend = chat.user1
    if chat.user1 == request.user:
        friend = chat.user2

    if chat.mode == chat.Mode.ON_CLOSE:
        chat.messages.all().delete()
    elif chat.mode == chat.Mode.AFTER_24HR:
        now = timezone.now()
        grace_period = now - timezone.timedelta(days=1)
        messages = messages.filter(created_at__gte=grace_period)

    return render(
        request,
        "pages/chat-details.html",
        {
            "friend": friend,
            "messages": messages,
            "chat_id": id,
            "chat": chat,
        },
    )


@login_required
@require_http_methods(["GET", "POST"])
def chat_settings_view(request, id):
    chat = get_object_or_404(Chat, pk=id)

    friend = chat.user2 if chat.user1 == request.user else chat.user1

    if request.method == "POST":
        mode = request.POST.get("mode")
        if mode in ["keep", "on_close", "after_24_hr"]:
            chat.mode = mode
            chat.save()
            return redirect("chat-details", id=chat.id)

    return render(
        request,
        "pages/chat-settings.html",
        {"chat": chat, "friend": friend},
    )


@login_required
def search_view(request):
    users = []
    friends = []
    unique_friends = []
    sent = []
    received = []

    search_username = request.GET.get("username")
    if search_username:
        users = (
            get_user_model()
            .objects.filter(username__icontains=search_username)
            .exclude(id=request.user.id)
        )

        queryset = FriendRequest.objects.filter(
            Q(from_user=request.user) | Q(to_user=request.user)
        )

        friends = queryset.filter(status=FriendRequest.StatusChoice.ACCEPTED)
        pending_requests = queryset.filter(status=FriendRequest.StatusChoice.PENDING)

        for friend in friends:
            if request.user == friend.from_user:
                unique_friends.append(friend.to_user.id)
            else:
                unique_friends.append(friend.from_user.id)

        for req in pending_requests:
            if request.user == req.from_user:
                sent.append(req.to_user.id)
            else:
                received.append(req.from_user.id)

    return render(
        request,
        "pages/search.html",
        {
            "users": users,
            "friends": unique_friends,
            "sent": sent,
            "received": received,
            "search": search_username or "",
        },
    )


@require_http_methods(["POST"])
@login_required
def send_invite(request, id):
    if id == request.user.id:
        return redirect("search-users")
    to_user = get_object_or_404(get_user_model(), id=id)

    try:
        FriendRequest.objects.create(from_user=request.user, to_user=to_user)
    except IntegrityError:
        return redirect("search-users")

    return redirect("search-users")


@login_required
@require_http_methods(["POST"])
def send_message(request, id):
    friend = get_object_or_404(get_user_model(), pk=id)

    if not are_friends(request.user, friend):
        return redirect("home")

    message = request.POST.get("message") or ""
    snap = request.FILES.get("image")

    chat = get_or_create_chat(request.user, friend)

    if message or snap:
        Message.objects.create(
            chat=chat,
            sender=request.user,
            reciever=friend,
            text=message,
            image=snap,
        )

        if snap:
            request.user.snap_score += 1
            friend.snap_score += 1

            request.user.save(update_fields=["snap_score"])
            friend.save(update_fields=["snap_score"])

        chat.last_message = timezone.now()
        chat.save(update_fields=["last_message"])

        update_streak(chat)

    return redirect("chat-details", id=chat.id)


@login_required
@require_http_methods(["GET"])
def friend_request_list_view(request):
    friend_requests = FriendRequest.objects.filter(
        status=FriendRequest.StatusChoice.PENDING, to_user=request.user
    )
    return render(
        request, "pages/friend-request.html", {"friend_requests": friend_requests}
    )


@login_required
@require_http_methods(["POST"])
def accept_friend_request(request, id):
    req = get_object_or_404(FriendRequest, pk=id)
    if req.to_user == request.user and req.status == FriendRequest.StatusChoice.PENDING:
        req.status = FriendRequest.StatusChoice.ACCEPTED
        req.save()
    return redirect("friend-requests")


@login_required
def map_view(request):
    friends = get_friends(request.user)
    locations = []
    for friend in friends:
        location = {
            "username": friend.username,
            "image": friend.avatar,
            "latitude": friend.latitude,
            "longitude": friend.longitude,
        }
        locations.append(location)

    return render(
    request,
    "pages/map.html",
    {
        "locations": locations,
    },
)



@login_required
def camera_view(request):
    friends = get_friends(request.user)
    selected_friend_id = request.GET.get("friend")

    try:
        selected_friend_id = int(selected_friend_id) if selected_friend_id else None
    except (TypeError, ValueError):
        selected_friend_id = None

    return render(
        request,
        "pages/camera.html",
        {"friends": friends, "selected_friend_id": selected_friend_id},
    )


@login_required
@require_http_methods(["POST"])
def send_snap_view(request):
    image_data = request.POST.get("image_data")
    friend_ids = request.POST.getlist("friend_ids")

    if not image_data or not friend_ids:
        return redirect("camera")

    image_text = image_data.split(",")[1]
    image_bytes = base64.b64decode(image_text)

    last_chat = None

    for friend_id in friend_ids:
        friend = get_object_or_404(get_user_model(), pk=friend_id)

        if not are_friends(request.user, friend):
            continue

        chat = get_or_create_chat(request.user, friend)

        Message.objects.create(
            chat=chat,
            sender=request.user,
            reciever=friend,
            image=ContentFile(image_bytes, name="snap.jpg"),
        )

        
        request.user.snap_score += 1
        request.user.save(update_fields=["snap_score"])

        
        friend.snap_score += 1
        friend.save(update_fields=["snap_score"])

        chat.last_message = timezone.now()
        chat.save(update_fields=["last_message"])

        update_streak(chat)
        last_chat = chat

    if last_chat and len(friend_ids) == 1:
        return redirect("chat-details", id=last_chat.id)

    return redirect("home")


from django.http import JsonResponse
from .models import Spotlight

@login_required
def spotlight_feed_view(request):
    spotlights = Spotlight.objects.all().order_by("-created_at")
    return render(request, "pages/spotlight_feed.html", {"spotlights": spotlights})


@login_required
@require_http_methods(["POST"])
def add_spotlight_view(request):
    title = request.POST.get("title", "Snap Spotlight")
    image_data = request.POST.get("image_data")
    file = request.FILES.get("file")
    
    if image_data:
        image_text = image_data.split(",")[1]
        image_bytes = base64.b64decode(image_text)
        Spotlight.objects.create(
            user=request.user,
            title=title,
            file=ContentFile(image_bytes, name="spotlight.jpg")
        )
    elif file:
        Spotlight.objects.create(
            user=request.user,
            title=title,
            file=file
        )
    return redirect("profile")


@login_required
@require_http_methods(["POST"])
def update_location(request):
    try:
        data = json.loads(request.body)
        lat = data.get("latitude")
        lng = data.get("longitude")
        if lat is not None and lng is not None:
            request.user.latitude = float(lat)
            request.user.longitude = float(lng)
            request.user.save(update_fields=["latitude", "longitude"])
            return JsonResponse({"status": "ok"})
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=400)
    return JsonResponse({"status": "ignored"}, status=400)