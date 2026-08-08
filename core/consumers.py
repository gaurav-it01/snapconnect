import json

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.contrib.auth import get_user_model
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils import timezone

from .models import Chat, Message


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        user = self.scope["user"]
        if not user.is_authenticated:
            await self.close()
            return

        self.chat_id = self.scope["url_route"]["kwargs"]["chat_id"]
        self.group_name = f"chat_{self.chat_id}"

        allowed = await self._is_chat_member(user.id, self.chat_id)
        if not allowed:
            await self.close()
            return

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, code):
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data=None, bytes_data=None):
        user = self.scope["user"]
        payload = json.loads(text_data)
        text = payload.get("message")

        if payload.get("screenshot"):
            saved = await self._save_screenshot_message(self.chat_id, user.id)
            await self.channel_layer.group_send(
                self.group_name,
                {
                    "type": "ss_message",
                    "message": saved["text"],
                    "sender_id": saved["sender_id"],
                    "sender_username": saved["sender_username"],
                    "created_at": saved["created_at"],
                },
            )
        elif "typing" in payload:
            await self.channel_layer.group_send(
                self.group_name,
                {
                    "type": "typing_message",
                    "sender_id": user.id,
                    "sender_username": user.username,
                    "is_typing": payload.get("typing"),
                },
            )
        elif payload.get("snap_viewed"):
            message_id = payload.get("message_id")
            if message_id:
                success = await self._mark_snap_viewed(message_id, user.id)
                if success:
                    await self.channel_layer.group_send(
                        self.group_name,
                        {
                            "type": "snap_viewed_message",
                            "message_id": message_id,
                            "sender_id": user.id,
                        },
                    )
        else:
            if not text:
                return
            saved = await self._save_message(self.chat_id, user.id, text)
            await self.channel_layer.group_send(
                self.group_name,
                {
                    "type": "chat_message",
                    "message": saved["text"],
                    "sender_id": saved["sender_id"],
                    "sender_username": saved["sender_username"],
                    "created_at": saved["created_at"],
                },
            )

    async def chat_message(self, event):
        await self.send(
            text_data=json.dumps(
                {
                    "message": event["message"],
                    "sender_id": event["sender_id"],
                    "is_system": False,
                    "sender_username": event["sender_username"],
                    "created_at": event["created_at"],
                }
            )
        )

    async def ss_message(self, event):
        await self.send(
            text_data=json.dumps(
                {
                    "message": event["message"],
                    "sender_id": event["sender_id"],
                    "is_system": True,
                    "sender_username": event["sender_username"],
                    "created_at": event["created_at"],
                }
            )
        )

    async def typing_message(self, event):
        await self.send(
            text_data=json.dumps(
                {
                    "type": "typing",
                    "sender_id": event["sender_id"],
                    "sender_username": event["sender_username"],
                    "is_typing": event["is_typing"],
                }
            )
        )

    async def snap_viewed_message(self, event):
        await self.send(
            text_data=json.dumps(
                {
                    "type": "snap_viewed",
                    "message_id": event["message_id"],
                    "sender_id": event["sender_id"],
                }
            )
        )

    @database_sync_to_async
    def _is_chat_member(self, user_id, chat_id):
        return (
            Chat.objects.filter(id=chat_id)
            .filter(Q(user1_id=user_id) | Q(user2_id=user_id))
            .exists()
        )

    @database_sync_to_async
    def _save_message(self, chat_id, sender_id, text_message):
        sender = get_object_or_404(get_user_model(), pk=sender_id)
        chat = Chat.objects.get(pk=chat_id)
        reciever = chat.user2
        if sender.id == chat.user2.id:
            reciever = chat.user1

        message = Message.objects.create(
            chat_id=chat.id, sender=sender, reciever=reciever, text=text_message
        )
        now = timezone.now()
        chat.last_message = now
        chat.save(update_fields=["last_message"])

        return {
            "text": message.text,
            "sender_id": sender_id,
            "sender_username": sender.get_username(),
            "created_at": now.isoformat(),
        }

    @database_sync_to_async
    def _save_screenshot_message(self, chat_id, sender_id):
        sender = get_object_or_404(get_user_model(), pk=sender_id)
        chat = Chat.objects.get(pk=chat_id)
        reciever = chat.user2
        if sender.id == chat.user2.id:
            reciever = chat.user1

        message = Message.objects.create(
            chat_id=chat.id,
            sender=sender,
            reciever=reciever,
            is_system=True,
            text=f"{sender.get_username()} took a screenshot of chat",
        )
        now = timezone.now()
        chat.last_message = now
        chat.save(update_fields=["last_message"])

        return {
            "text": message.text,
            "sender_id": sender_id,
            "sender_username": sender.get_username(),
            "created_at": now.isoformat(),
        }

    @database_sync_to_async
    def _mark_snap_viewed(self, message_id, user_id):
        try:
            message = Message.objects.get(
                pk=message_id,
                chat_id=self.chat_id
            )

            # Only the receiver can view a snap.
            if (
                message.image
                and not message.is_viewed
                and message.reciever_id == user_id
            ):
                message.is_viewed = True
                message.viewed_at = timezone.now()

                message.save(
                    update_fields=[
                        "is_viewed",
                        "viewed_at"
                    ]
                )

                return True
        except Message.DoesNotExist:
            pass

        return False
    

