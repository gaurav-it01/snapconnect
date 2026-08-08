import base64
import binascii
import json

from django.conf import settings
from django.core.files.base import ContentFile
from django.db import IntegrityError
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from django.contrib.auth import (
    get_user_model,
    login,
    logout,
)
from django.contrib.auth.decorators import login_required

from . import forms
from .models import Chat, FriendRequest, Message, Spotlight
from .utils import (
    are_friends,
    get_friends,
    get_or_create_chat,
    update_streak,
)



@require_http_methods(["GET", "POST"])
def register_view(request):

    if request.user.is_authenticated:
        return redirect("home")

    form = forms.RegisterForm(
        request.POST or None,
        request.FILES or None
    )

    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user)
        return redirect("home")

    return render(
        request,
        "accounts/register.html",
        {"form": form}
    )


@require_http_methods(["GET", "POST"])
def login_view(request):

    if request.user.is_authenticated:
        return redirect("home")

    form = forms.LoginForm(
        request,
        data=request.POST or None
    )

    if request.method == "POST" and form.is_valid():
        login(request, form.get_user())
        return redirect("home")

    return render(
        request,
        "accounts/login.html",
        {"form": form}
    )


@require_http_methods(["POST"])
@login_required
def logout_view(request):
    logout(request)
    return redirect("login")


@login_required
def profile_view(request):

    spotlights = request.user.spotlights.all().order_by(
        "-created_at"
    )

    return render(
        request,
        "accounts/profile.html",
        {"spotlights": spotlights}
    )


@login_required
@require_http_methods(["GET", "POST"])
def change_avatar_view(request):

    form = forms.ChangeAvatarForm(
        request.POST or None,
        request.FILES or None,
        instance=request.user,
    )

    if request.method == "POST" and form.is_valid():

        old_name = (
            request.user.avatar.name
            if request.user.avatar
            else None
        )

        form.save()

        defaults = (
            "snaps/default.jpg",
            "avatar/default.jpg",
        )

        if (
            old_name
            and old_name not in defaults
            and old_name != request.user.avatar.name
        ):
            request.user.avatar.storage.delete(old_name)

        return redirect("profile")

    return render(
        request,
        "accounts/change-avatar.html",
        {"form": form}
    )


@login_required
@require_http_methods(["GET", "POST"])
def edit_username_view(request):

    form = forms.EditUsernameForm(
        request.POST or None,
        instance=request.user
    )

    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect("profile")

    return render(
        request,
        "accounts/edit-username.html",
        {"form": form}
    )



@login_required
def home(request):

    friends = get_friends(request.user)
    locationform = forms.LocationForm()

    chat_list = []

    for friend in friends:

        chat = get_or_create_chat(
            request.user,
            friend
        )

        last_message = (
            chat.messages
            .order_by("-created_at")
            .first()
        )

        if last_message is None:
            last_message_text = "say Hii"

        elif last_message.image:
            last_message_text = "new snap"

        else:
            last_message_text = last_message.text

        chat_list.append(
            (
                friend,
                chat,
                last_message_text,
                last_message
            )
        )

    chat_list.sort(
        key=lambda row: row[1].last_message,
        reverse=True
    )

    return render(
        request,
        "pages/chat.html",
        {
            "chats": chat_list,
            "locationform": locationform,
        }
    )



@login_required
def chat_details_view(request, id):

    # SECURITY FIX:
    # User must actually belong to this chat.
    chat = get_object_or_404(
        Chat,
        Q(user1=request.user) | Q(user2=request.user),
        pk=id
    )

    messages = (
        chat.messages
        .all()
        .order_by("created_at")
    )

    update_streak(chat)

    if chat.user1 == request.user:
        friend = chat.user2
    else:
        friend = chat.user1

    # Keep your existing disappearing-message behavior.
    if chat.mode == Chat.Mode.ON_CLOSE:

        chat.messages.all().delete()

    elif chat.mode == Chat.Mode.AFTER_24HR:

        now = timezone.now()
        grace_period = now - timezone.timedelta(days=1)

        messages = messages.filter(
            created_at__gte=grace_period
        )

    return render(
        request,
        "pages/chat-details.html",
        {
            "friend": friend,
            "messages": messages,
            "chat_id": id,
            "chat": chat,
        }
    )



@login_required
@require_http_methods(["GET", "POST"])
def chat_settings_view(request, id):

    # SECURITY FIX:
    # Only participants can access/change chat settings.
    chat = get_object_or_404(
        Chat,
        Q(user1=request.user) | Q(user2=request.user),
        pk=id
    )

    if chat.user1 == request.user:
        friend = chat.user2
    else:
        friend = chat.user1

    if request.method == "POST":

        mode = request.POST.get("mode")

        allowed_modes = {
            Chat.Mode.KEEP,
            Chat.Mode.ON_CLOSE,
            Chat.Mode.AFTER_24HR,
        }

        if mode in allowed_modes:

            chat.mode = mode
            chat.save(update_fields=["mode", "updated_at"])

            return redirect(
                "chat-details",
                id=chat.id
            )

    return render(
        request,
        "pages/chat-settings.html",
        {
            "chat": chat,
            "friend": friend,
        }
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
            .objects
            .filter(
                username__icontains=search_username
            )
            .exclude(id=request.user.id)
        )

        queryset = FriendRequest.objects.filter(
            Q(from_user=request.user)
            | Q(to_user=request.user)
        )

        friends = queryset.filter(
            status=FriendRequest.StatusChoice.ACCEPTED
        )

        pending_requests = queryset.filter(
            status=FriendRequest.StatusChoice.PENDING
        )

        for friend in friends:

            if request.user == friend.from_user:
                unique_friends.append(
                    friend.to_user.id
                )
            else:
                unique_friends.append(
                    friend.from_user.id
                )

        for req in pending_requests:

            if request.user == req.from_user:
                sent.append(
                    req.to_user.id
                )
            else:
                received.append(
                    req.from_user.id
                )

    return render(
        request,
        "pages/search.html",
        {
            "users": users,
            "friends": unique_friends,
            "sent": sent,
            "received": received,
            "search": search_username or "",
        }
    )



@login_required
@require_http_methods(["POST"])
def send_invite(request, id):

    if id == request.user.id:
        return redirect("search-users")

    to_user = get_object_or_404(
        get_user_model(),
        id=id
    )

    try:

        FriendRequest.objects.create(
            from_user=request.user,
            to_user=to_user
        )

    except IntegrityError:
        # Existing request
        pass

    return redirect("search-users")


@login_required
@require_http_methods(["GET"])
def friend_request_list_view(request):

    friend_requests = (
        FriendRequest.objects
        .filter(
            status=FriendRequest.StatusChoice.PENDING,
            to_user=request.user
        )
        .select_related("from_user")
    )

    return render(
        request,
        "pages/friend-request.html",
        {
            "friend_requests": friend_requests
        }
    )


@login_required
@require_http_methods(["POST"])
def accept_friend_request(request, id):

    req = get_object_or_404(
        FriendRequest,
        pk=id
    )

    if (
        req.to_user == request.user
        and req.status
        == FriendRequest.StatusChoice.PENDING
    ):

        req.status = (
            FriendRequest.StatusChoice.ACCEPTED
        )

        req.save(update_fields=["status"])

    return redirect("friend-requests")


@login_required
@require_http_methods(["POST"])
def reject_friend_request(request, id):

    req = get_object_or_404(
        FriendRequest,
        pk=id
    )

    if (
        req.to_user == request.user
        and req.status
        == FriendRequest.StatusChoice.PENDING
    ):

        req.status = (
            FriendRequest.StatusChoice.REJECTED
        )

        req.save(update_fields=["status"])

    return redirect("friend-requests")



@login_required
@require_http_methods(["POST"])
def send_message(request, id):

    friend = get_object_or_404(
        get_user_model(),
        pk=id
    )

    # Only friends can message each other.
    if not are_friends(
        request.user,
        friend
    ):
        return redirect("home")

    message = request.POST.get(
        "message"
    ) or ""

    snap = request.FILES.get(
        "image"
    )

    chat = get_or_create_chat(
        request.user,
        friend
    )

    if message or snap:

        Message.objects.create(
            chat=chat,
            sender=request.user,
            reciever=friend,  # KEEP THIS
            text=message,
            image=snap,
        )

        if snap:

            request.user.snap_score += 1
            friend.snap_score += 1

            request.user.save(
                update_fields=["snap_score"]
            )

            friend.save(
                update_fields=["snap_score"]
            )

        chat.last_message = timezone.now()

        chat.save(
            update_fields=["last_message"]
        )

        update_streak(chat)

    return redirect(
        "chat-details",
        id=chat.id
    )



@login_required
def map_view(request):

    friends = get_friends(
        request.user
    )

    locations = []

    for friend in friends:

        locations.append(
            {
                "username": friend.username,
                "image": friend.avatar,
                "latitude": friend.latitude,
                "longitude": friend.longitude,
            }
        )

    return render(
        request,
        "pages/map.html",
        {
            "locations": locations,
        }
    )


@login_required
def camera_view(request):

    friends = get_friends(
        request.user
    )

    selected_friend_id = request.GET.get(
        "friend"
    )

    try:

        selected_friend_id = (
            int(selected_friend_id)
            if selected_friend_id
            else None
        )

    except (TypeError, ValueError):

        selected_friend_id = None

    return render(
        request,
        "pages/camera.html",
        {
            "friends": friends,
            "selected_friend_id": selected_friend_id,
        }
    )




@login_required
@require_http_methods(["POST"])
def send_snap_view(request):

    image_data = request.POST.get(
        "image_data"
    )

    friend_ids = request.POST.getlist(
        "friend_ids"
    )

    if not image_data or not friend_ids:
        return redirect("camera")

    # Safe Base64 processing
    try:

        if "," not in image_data:
            return redirect("camera")

        image_text = image_data.split(
            ",",
            1
        )[1]

        image_bytes = base64.b64decode(
            image_text,
            validate=True
        )

    except (
        ValueError,
        IndexError,
        binascii.Error
    ):

        return redirect("camera")

    last_chat = None

    for friend_id in friend_ids:

        friend = get_object_or_404(
            get_user_model(),
            pk=friend_id
        )

        # Never allow sending snaps to non-friends.
        if not are_friends(
            request.user,
            friend
        ):
            continue

        chat = get_or_create_chat(
            request.user,
            friend
        )

        Message.objects.create(
            chat=chat,
            sender=request.user,
            reciever=friend,  # KEEP THIS
            image=ContentFile(
                image_bytes,
                name="snap.jpg"
            ),
        )

        request.user.snap_score += 1
        friend.snap_score += 1

        request.user.save(
            update_fields=["snap_score"]
        )

        friend.save(
            update_fields=["snap_score"]
        )

        chat.last_message = timezone.now()

        chat.save(
            update_fields=["last_message"]
        )

        update_streak(chat)

        last_chat = chat

    if (
        last_chat
        and len(friend_ids) == 1
    ):
        return redirect(
            "chat-details",
            id=last_chat.id
        )

    return redirect("home")




@login_required
def spotlight_feed_view(request):

    spotlights = (
        Spotlight.objects
        .all()
        .order_by("-created_at")
    )

    return render(
        request,
        "pages/spotlight_feed.html",
        {
            "spotlights": spotlights
        }
    )


@login_required
@require_http_methods(["POST"])
def add_spotlight_view(request):

    title = request.POST.get(
        "title",
        "Snap Spotlight"
    )

    image_data = request.POST.get(
        "image_data"
    )

    file = request.FILES.get(
        "file"
    )

    if image_data:

        try:

            if "," not in image_data:
                return redirect("profile")

            image_text = image_data.split(
                ",",
                1
            )[1]

            image_bytes = base64.b64decode(
                image_text,
                validate=True
            )

        except (
            ValueError,
            IndexError,
            binascii.Error
        ):

            return redirect("profile")

        Spotlight.objects.create(
            user=request.user,
            title=title,
            file=ContentFile(
                image_bytes,
                name="spotlight.jpg"
            )
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

        data = json.loads(
            request.body
        )

        lat = data.get(
            "latitude"
        )

        lng = data.get(
            "longitude"
        )

        if lat is None or lng is None:

            return JsonResponse(
                {
                    "status": "ignored"
                },
                status=400
            )

        lat = float(lat)
        lng = float(lng)

        # Basic geographic validation
        if not (-90 <= lat <= 90):
            return JsonResponse(
                {
                    "status": "error",
                    "message": "Invalid latitude"
                },
                status=400
            )

        if not (-180 <= lng <= 180):
            return JsonResponse(
                {
                    "status": "error",
                    "message": "Invalid longitude"
                },
                status=400
            )

        request.user.latitude = lat
        request.user.longitude = lng

        request.user.save(
            update_fields=[
                "latitude",
                "longitude"
            ]
        )

        return JsonResponse(
            {
                "status": "ok"
            }
        )

    except (
        TypeError,
        ValueError,
        json.JSONDecodeError
    ):

        return JsonResponse(
            {
                "status": "error",
                "message": "Invalid location data"
            },
            status=400
        )