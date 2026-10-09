"""URL routes for the chat app."""
from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

urlpatterns = [
    path("", views.room_list_view, name="room_list"),
    path("signup/", views.signup_view, name="signup"),
    path(
        "login/",
        auth_views.LoginView.as_view(template_name="chat/login.html"),
        name="login",
    ),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("rooms/", views.room_list_view, name="room_list"),
    path("rooms/<int:room_id>/", views.room_detail_view, name="room_detail"),
    path(
        "rooms/<int:room_id>/upload/",
        views.upload_attachment_view,
        name="upload_attachment",
    ),
]
