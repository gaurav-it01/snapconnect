from typing import List
from datetime import timedelta

from django.db.models import Q
from django.utils import timezone

from .models import FriendRequest, Chat, SnapUser


def are_friends(user1, user2):
    return (
        FriendRequest.objects.filter(
            Q(from_user=user1, to_user=user2)
            | Q(from_user=user2, to_user=user1)
        )
        .filter(status=FriendRequest.StatusChoice.ACCEPTED)
        .exists()
    )


def get_friends(user) -> List[SnapUser]:
    friend_requests = (
        FriendRequest.objects.filter(
            status=FriendRequest.StatusChoice.ACCEPTED
        )
        .filter(
            Q(from_user=user) | Q(to_user=user)
        )
    )

    friends = []

    for fr in friend_requests:
        if user == fr.from_user:
            friends.append(fr.to_user)
        else:
            friends.append(fr.from_user)

    return friends


def get_or_create_chat(user1, user2):
    if user1.id > user2.id:
        user1, user2 = user2, user1

    chat, _ = Chat.objects.get_or_create(
        user1=user1,
        user2=user2
    )

    return chat


def has_user_sent_snap_today(chat, user):
    today = timezone.now().date()

    return (
        chat.messages
        .filter(
            sender=user,
            created_at__date=today
        )
        .exclude(image="")
        .exclude(image=None)
        .exists()
    )


def is_continuous_streak(last_streak_updated_at, now):
    return (
        last_streak_updated_at.date() + timedelta(days=1)
        == now.date()
    )


def update_streak(chat: Chat):
    now = timezone.now()

    user1_snap = has_user_sent_snap_today(
        chat,
        chat.user1
    )

    user2_snap = has_user_sent_snap_today(
        chat,
        chat.user2
    )

    if user1_snap and user2_snap:

        if (
            chat.streak_updated_at.date() == now.date()
            and chat.streak > 0
        ):
            return

        if is_continuous_streak(
            chat.streak_updated_at,
            now
        ):
            chat.streak += 1
        else:
            chat.streak = 1

        chat.streak_updated_at = now

        chat.save()

    else:

        days_passed = (
            now.date()
            - chat.streak_updated_at.date()
        ).days

        if chat.streak > 0 and days_passed > 1:
            chat.streak = 0

            chat.save(
                update_fields=["streak"]
            )