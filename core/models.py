from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings
from django.utils import timezone



class SnapUser(AbstractUser):
    snap_score = models.PositiveIntegerField(default=0)

    avatar = models.ImageField(
        upload_to="avatar",
        default="avatar/default.jpg"
    )

    latitude = models.FloatField(
        null=True,
        blank=True
    )

    longitude = models.FloatField(
        null=True,
        blank=True
    )

    def __str__(self):
        return self.username



class FriendRequest(models.Model):

    class StatusChoice(models.TextChoices):
        PENDING = "pending", "Pending"
        ACCEPTED = "accepted", "Accepted"
        REJECTED = "rejected", "Rejected"

    from_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="sent_requests"
    )

    to_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="received_requests"
    )

    status = models.CharField(
        max_length=10,
        choices=StatusChoice.choices,
        default=StatusChoice.PENDING
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["from_user", "to_user"],
                name="unique_friend_request"
            ),
            models.CheckConstraint(
                condition=~models.Q(
                    from_user=models.F("to_user")
                ),
                name="prevent_self_friend_request"
            ),
        ]

    def __str__(self):
        return (
            f"Friend: {self.from_user} -> "
            f"{self.to_user}: {self.status}"
        )




class Chat(models.Model):

    class Mode(models.TextChoices):
        KEEP = "keep", "Keep"
        ON_CLOSE = "on_close", "On Close"
        AFTER_24HR = "after_24_hr", "After 24 Hours"

    user1 = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="user1_chats"
    )

    user2 = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="user2_chats"
    )

    mode = models.CharField(
        max_length=16,
        choices=Mode.choices,
        default=Mode.ON_CLOSE
    )

    streak = models.PositiveIntegerField(
        default=0,
        editable=False
    )

    streak_updated_at = models.DateTimeField(
        default=timezone.now
    )

    last_message = models.DateTimeField(
        default=timezone.now
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=~models.Q(
                    user1=models.F("user2")
                ),
                name="prevent_self_chat"
            )
        ]

    def __str__(self):
        return f"Chat: {self.user1} <-> {self.user2}"



class Message(models.Model):

    chat = models.ForeignKey(
        Chat,
        on_delete=models.CASCADE,
        related_name="messages"
    )

    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="sent_messages"
    )

    reciever = models.ForeignKey(
    settings.AUTH_USER_MODEL,
    on_delete=models.CASCADE,
    related_name="recieved_messages"
)

    is_system = models.BooleanField(
        default=False
    )

    image = models.ImageField(
        upload_to="snaps",
        null=True,
        blank=True
    )

    text = models.TextField(
        blank=True
    )

    is_viewed = models.BooleanField(
        default=False
    )

    viewed_at = models.DateTimeField(
        null=True,
        blank=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return f"Message {self.sender} -> {self.reciever}"



class Spotlight(models.Model):

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="spotlights"
    )

    title = models.CharField(
        max_length=64,
        default="Spotlight"
    )

    file = models.FileField(
        upload_to="spotlights"
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return f"Spotlight: {self.title} by {self.user.username}"