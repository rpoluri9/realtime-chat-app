"""Tests: signup creates a user + token, login works."""
import pytest
from django.contrib.auth.models import User

from chat.models import Token


@pytest.mark.django_db
def test_signup_creates_user_and_token(client):
    res = client.post(
        "/signup/",
        {
            "username": "alice",
            "email": "alice@example.com",
            "password1": "secret12345",
            "password2": "secret12345",
        },
    )
    assert res.status_code == 302  # redirect to rooms on success
    user = User.objects.get(username="alice")
    assert Token.objects.filter(user=user).exists()


@pytest.mark.django_db
def test_login_works(client):
    User.objects.create_user(username="bob", password="secret12345")
    res = client.post("/login/", {"username": "bob", "password": "secret12345"})
    assert res.status_code == 302
    assert "_auth_user_id" in client.session


@pytest.mark.django_db
def test_login_with_wrong_password_fails(client):
    User.objects.create_user(username="carol", password="secret12345")
    res = client.post("/login/", {"username": "carol", "password": "wrong"})
    assert res.status_code == 200  # form shown again, no redirect
    assert "_auth_user_id" not in client.session


@pytest.mark.django_db
def test_rooms_page_requires_login(client):
    res = client.get("/rooms/")
    assert res.status_code == 302
    assert "/login/" in res["Location"]
