from . import views
from django.urls import path

urlpatterns = [
    path("", views.home, name="home"),
    path("login/", views.login_view, name="login"),
    path("register/", views.register_view, name="register-user"),
    path("profile/", views.profile_view, name="profile"),
    path("profile/avatar/", views.change_avatar_view, name="change-avatar"),
    path("profile/username/", views.edit_username_view, name="edit-username"),
    path("logout/", views.logout_view, name="logout"),
    path("search/", views.search_view, name="search-users"),
    path("camera/", views.camera_view, name="camera"),
    path("send-snap/", views.send_snap_view, name="send-snap"),
    path("send-invite/<int:id>", views.send_invite, name="send-invite"),
    path("chat-details/<int:id>", views.chat_details_view, name="chat-details"),
    path("chat-details/<int:id>/settings/",views.chat_settings_view,name="chat-settings",),
    path("send-message/<int:id>", views.send_message, name="send-message"),
    path("friend-requests/", views.friend_request_list_view, name="friend-requests"),
    path("accept-requests/<int:id>/", views.accept_friend_request, name="accept-friend"),
    path("map/", views.map_view, name="map-view"),
    path("location/update/", views.update_location, name="update-location"),
    path("spotlight/", views.spotlight_feed_view, name="spotlight-feed"),
    path("profile/spotlight/add/", views.add_spotlight_view, name="add-spotlight"),
]
