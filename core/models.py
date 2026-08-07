from django.db import models
from django.contrib.auth.models import AbstractUser
from django.contrib.auth import get_user_model
from django.utils import timezone


# Create your models here.
class SnapUser(AbstractUser):
    snap_score = models.PositiveIntegerField(default=0)
    avatar = models.ImageField(upload_to="avatar", default="avatar/default.jpg")
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)


class FriendRequest(models.Model):
    class StatusChoice(models.TextChoices):
        PENDING = "pending", "Pending"
        ACCEPTED = "accepted", "Accepted"

    from_user = models.ForeignKey(
        to=get_user_model(), on_delete=models.CASCADE, related_name="sent_requests"
    )
    to_user = models.ForeignKey(
        to=get_user_model(), on_delete=models.CASCADE, related_name="recieved_requests"
    )
    status = models.CharField(
        max_length=10, choices=StatusChoice.choices, default=StatusChoice.PENDING
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("from_user", "to_user")

    def __str__(self):
        return f"Friend: {self.from_user} -> {self.to_user}: {self.status}"


class Chat(models.Model):
    class Mode(models.TextChoices):
        KEEP = "keep", "Keep"
        ON_CLOSE = "on_close", "ON_CLOSE"
        AFTER_24HR = "after_24_hr", "AFTER_24_HR"

    user1 = models.ForeignKey(
        to=get_user_model(), on_delete=models.CASCADE, related_name="user1_chats"
    )
    user2 = models.ForeignKey(
        to=get_user_model(), on_delete=models.CASCADE, related_name="user2_chats"
    )
    mode = models.CharField(max_length=16, choices=Mode.choices, default=Mode.ON_CLOSE)
    streak = models.PositiveIntegerField(default=0, editable=False)
    streak_updated_at = models.DateTimeField(default=timezone.now)
    last_message = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Chat: {self.user1} <-> {self.user2}"


class Message(models.Model):
    chat = models.ForeignKey(to=Chat, on_delete=models.CASCADE, related_name="messages")
    sender = models.ForeignKey(
        to=get_user_model(), on_delete=models.CASCADE, related_name="sent_messages"
    )
    reciever = models.ForeignKey(
        to=get_user_model(), on_delete=models.CASCADE, related_name="recieved_messages"
    )
    is_system = models.BooleanField(default=False)
    image = models.ImageField(upload_to="snaps", null=True, blank=True)
    text = models.TextField(blank=True)
    is_viewed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Message {self.sender} -> {self.reciever}"





class Spotlight(models.Model):
    user = models.ForeignKey(
        to=get_user_model(), on_delete=models.CASCADE, related_name="spotlights"
    )
    title = models.CharField(max_length=64, default="Spotlight")
    file = models.FileField(upload_to="spotlights")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Spotlight: {self.title} by {self.user.username}"



