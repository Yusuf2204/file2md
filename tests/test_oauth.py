from unittest.mock import AsyncMock, patch
import pytest
from fastapi.testclient import TestClient
from app.database import Base, engine, SessionLocal
from app.models import User
from app.main import app

Base.metadata.create_all(bind=engine)
client = TestClient(app, follow_redirects=False)


@pytest.fixture(autouse=True)
def cleanup():
    db = SessionLocal()
    db.query(User).filter(User.email.like("%@oauth-test.local")).delete()
    db.commit()
    db.close()
    yield
    db = SessionLocal()
    db.query(User).filter(User.email.like("%@oauth-test.local")).delete()
    db.commit()
    db.close()


def test_google_login_not_configured(monkeypatch):
    monkeypatch.delenv("GOOGLE_CLIENT_ID", raising=False)
    monkeypatch.delenv("GOOGLE_CLIENT_SECRET", raising=False)

    res = client.get("/api/auth/google/login")
    assert res.status_code == 302
    assert "auth_error" in res.headers["location"]
    from urllib.parse import unquote
    assert "Fitur login Google sedang dalam tahap pengembangan" in unquote(res.headers["location"])


def test_google_login_redirect_url(monkeypatch):
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "dummy-google-client-id")
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "dummy-google-client-secret")
    monkeypatch.setenv("APP_BASE_URL", "http://localhost:8031")

    res = client.get("/api/auth/google/login")
    assert res.status_code == 302
    target_url = res.headers["location"]
    assert target_url.startswith("https://accounts.google.com/o/oauth2/v2/auth?")
    assert "client_id=dummy-google-client-id" in target_url
    assert "redirect_uri=http%3A%2F%2Flocalhost%3A8031%2Fapi%2Fauth%2Fgoogle%2Fcallback" in target_url


def test_google_callback_success(monkeypatch):
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "dummy-google-client-id")
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "dummy-google-client-secret")
    monkeypatch.setenv("APP_BASE_URL", "http://localhost:8031")

    # Mock respons httpx untuk token dan userinfo Google
    class MockTokenResponse:
        status_code = 200
        def json(self):
            return {"access_token": "mock_google_token_123"}

    class MockUserinfoResponse:
        status_code = 200
        def json(self):
            return {"email": "alex@oauth-test.local", "name": "Alex Google"}

    mock_client = AsyncMock()
    mock_client.post.return_value = MockTokenResponse()
    mock_client.get.return_value = MockUserinfoResponse()

    with patch("httpx.AsyncClient") as mock_async_client_cls:
        mock_async_client_cls.return_value.__aenter__.return_value = mock_client

        res = client.get("/api/auth/google/callback?code=mock_google_auth_code")
        assert res.status_code == 302
        assert "auth_success" in res.headers["location"]
        assert "access_token" in res.cookies

        # Verifikasi user tersimpan di DB
        db = SessionLocal()
        user = db.query(User).filter(User.email == "alex@oauth-test.local").first()
        assert user is not None
        assert user.tier == "free"
        db.close()


def test_github_login_not_configured(monkeypatch):
    monkeypatch.delenv("GITHUB_CLIENT_ID", raising=False)
    monkeypatch.delenv("GITHUB_CLIENT_SECRET", raising=False)

    res = client.get("/api/auth/github/login")
    assert res.status_code == 302
    assert "auth_error" in res.headers["location"]
    from urllib.parse import unquote
    assert "Fitur login GitHub sedang dalam tahap pengembangan" in unquote(res.headers["location"])


def test_github_login_redirect_url(monkeypatch):
    monkeypatch.setenv("GITHUB_CLIENT_ID", "dummy-github-client-id")
    monkeypatch.setenv("GITHUB_CLIENT_SECRET", "dummy-github-client-secret")
    monkeypatch.setenv("APP_BASE_URL", "http://localhost:8031")

    res = client.get("/api/auth/github/login")
    assert res.status_code == 302
    target_url = res.headers["location"]
    assert target_url.startswith("https://github.com/login/oauth/authorize?")
    assert "client_id=dummy-github-client-id" in target_url
    assert "redirect_uri=http%3A%2F%2Flocalhost%3A8031%2Fapi%2Fauth%2Fgithub%2Fcallback" in target_url


def test_github_callback_success(monkeypatch):
    monkeypatch.setenv("GITHUB_CLIENT_ID", "dummy-github-client-id")
    monkeypatch.setenv("GITHUB_CLIENT_SECRET", "dummy-github-client-secret")
    monkeypatch.setenv("APP_BASE_URL", "http://localhost:8031")

    # Mock respons httpx untuk token dan emails GitHub
    class MockTokenResponse:
        status_code = 200
        def json(self):
            return {"access_token": "mock_github_token_456"}

    class MockEmailsResponse:
        status_code = 200
        def json(self):
            return [
                {"email": "secondary@oauth-test.local", "primary": False, "verified": True},
                {"email": "octocat@oauth-test.local", "primary": True, "verified": True},
            ]

    mock_client = AsyncMock()
    mock_client.post.return_value = MockTokenResponse()
    mock_client.get.return_value = MockEmailsResponse()

    with patch("httpx.AsyncClient") as mock_async_client_cls:
        mock_async_client_cls.return_value.__aenter__.return_value = mock_client

        res = client.get("/api/auth/github/callback?code=mock_github_auth_code")
        assert res.status_code == 302
        assert "auth_success" in res.headers["location"]
        assert "access_token" in res.cookies

        # Verifikasi user tersimpan di DB
        db = SessionLocal()
        user = db.query(User).filter(User.email == "octocat@oauth-test.local").first()
        assert user is not None
        assert user.tier == "free"
        db.close()
