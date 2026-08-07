from django.contrib.auth.admin import UserAdmin
from django.contrib import admin
from .models import FriendRequest, Message, SnapUser, Chat

# Register your models here.


class MyUserAdmin(UserAdmin):
    model = SnapUser
    fieldsets = UserAdmin.fieldsets + (
        (None, {"fields": ("avatar", "longitude", "latitude")}),
    )


admin.site.register(SnapUser, MyUserAdmin)
admin.site.register(FriendRequest)
admin.site.register(Message)
admin.site.register(Chat)
