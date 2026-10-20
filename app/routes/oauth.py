import os
import secrets
import urllib.parse
from typing import Annotated
import httpx
from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User
from app.services.security import create_access_token, hash_password

router = APIRouter(prefix="/api/auth", tags=["OAuth"])


def _get_redirect_uri(request: Request, provider: str) -> str:
    """Menghitung redirect callback URI secara konsisten."""
    app_base_url = os.getenv("APP_BASE_URL", "").rstrip("/")
    if app_base_url:
        return f"{app_base_url}/api/auth/{provider}/callback"
    return f"{str(request.base_url).rstrip('/')}/api/auth/{provider}/callback"


def _login_or_register_oauth_user(
    email: str,
    db: Session,
    provider: str,
) -> tuple[str, bool]:
    """Mencari user berdasarkan email atau mendaftarkan user baru dari OAuth provider."""
    email = email.strip().lower()
    user = db.query(User).filter(User.email == email).first()
    is_new = False

    if not user:
        is_new = True
        user = User(
            email=email,
            # Password acak yang di-hash dengan kuat untuk keamanan akun OAuth
            hashed_password=hash_password(f"oauth_{provider}_{secrets.token_urlsafe(32)}"),
            tier="free",
            is_active=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    token = create_access_token(
        data={"sub": str(user.id), "email": user.email, "tier": user.tier}
    )
    return token, is_new


# ==========================================
# Google OAuth 2.0
# ==========================================

@router.get("/google/login", summary="Redirect ke halaman login Google OAuth 2.0")
def google_login(request: Request):
    client_id = os.getenv("GOOGLE_CLIENT_ID", "").strip()
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET", "").strip()

    if not client_id or not client_secret:
        msg = urllib.parse.quote("Fitur login Google sedang dalam tahap pengembangan.")
        return RedirectResponse(url=f"/?auth_error={msg}", status_code=status.HTTP_302_FOUND)

    redirect_uri = _get_redirect_uri(request, "google")
    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "online",
        "prompt": "select_account",
    }
    google_auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?{urllib.parse.urlencode(params)}"
    return RedirectResponse(url=google_auth_url, status_code=status.HTTP_302_FOUND)


@router.get("/google/callback", summary="Callback OAuth Google")
async def google_callback(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
):
    if error := request.query_params.get("error"):
        msg = urllib.parse.quote(f"Login Google dibatalkan: {error}")
        return RedirectResponse(url=f"/?auth_error={msg}", status_code=status.HTTP_302_FOUND)

    code = request.query_params.get("code")
    if not code:
        msg = urllib.parse.quote("Kode otentikasi Google tidak ditemukan.")
        return RedirectResponse(url=f"/?auth_error={msg}", status_code=status.HTTP_302_FOUND)

    client_id = os.getenv("GOOGLE_CLIENT_ID", "").strip()
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET", "").strip()
    redirect_uri = _get_redirect_uri(request, "google")

    try:
        async with httpx.AsyncClient(timeout=12.0) as client:
            token_resp = await client.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "code": code,
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "redirect_uri": redirect_uri,
                    "grant_type": "authorization_code",
                },
            )
            if token_resp.status_code != 200:
                msg = urllib.parse.quote("Gagal menukar kode otentikasi Google dengan access token.")
                return RedirectResponse(url=f"/?auth_error={msg}", status_code=status.HTTP_302_FOUND)

            token_data = token_resp.json()
            access_token = token_data.get("access_token")

            userinfo_resp = await client.get(
                "https://www.googleapis.com/oauth2/v3/userinfo",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            if userinfo_resp.status_code != 200:
                msg = urllib.parse.quote("Gagal mengambil informasi profil dari akun Google.")
                return RedirectResponse(url=f"/?auth_error={msg}", status_code=status.HTTP_302_FOUND)

            userinfo = userinfo_resp.json()
            email = userinfo.get("email")

        if not email:
            msg = urllib.parse.quote("Alamat email tidak ditemukan pada profil akun Google Anda.")
            return RedirectResponse(url=f"/?auth_error={msg}", status_code=status.HTTP_302_FOUND)

        token, is_new = _login_or_register_oauth_user(email=email, db=db, provider="google")
        success_msg = urllib.parse.quote(f"Selamat datang! Berhasil masuk dengan Google ({email}).")
        response = RedirectResponse(url=f"/?auth_success={success_msg}", status_code=status.HTTP_302_FOUND)
        response.set_cookie(key="access_token", value=token, httponly=True, samesite="lax")
        return response

    except Exception as exc:
        msg = urllib.parse.quote(f"Terjadi kesalahan saat otentikasi Google: {str(exc)}")
        return RedirectResponse(url=f"/?auth_error={msg}", status_code=status.HTTP_302_FOUND)


# ==========================================
# GitHub OAuth
# ==========================================

@router.get("/github/login", summary="Redirect ke halaman login GitHub OAuth")
def github_login(request: Request):
    client_id = os.getenv("GITHUB_CLIENT_ID", "").strip()
    client_secret = os.getenv("GITHUB_CLIENT_SECRET", "").strip()

    if not client_id or not client_secret:
        msg = urllib.parse.quote("Fitur login GitHub sedang dalam tahap pengembangan.")
        return RedirectResponse(url=f"/?auth_error={msg}", status_code=status.HTTP_302_FOUND)

    redirect_uri = _get_redirect_uri(request, "github")
    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "scope": "user:email",
    }
    github_auth_url = f"https://github.com/login/oauth/authorize?{urllib.parse.urlencode(params)}"
    return RedirectResponse(url=github_auth_url, status_code=status.HTTP_302_FOUND)


@router.get("/github/callback", summary="Callback OAuth GitHub")
async def github_callback(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
):
    if error := request.query_params.get("error"):
        msg = urllib.parse.quote(f"Login GitHub dibatalkan: {error}")
        return RedirectResponse(url=f"/?auth_error={msg}", status_code=status.HTTP_302_FOUND)

    code = request.query_params.get("code")
    if not code:
        msg = urllib.parse.quote("Kode otentikasi GitHub tidak ditemukan.")
        return RedirectResponse(url=f"/?auth_error={msg}", status_code=status.HTTP_302_FOUND)

    client_id = os.getenv("GITHUB_CLIENT_ID", "").strip()
    client_secret = os.getenv("GITHUB_CLIENT_SECRET", "").strip()
    redirect_uri = _get_redirect_uri(request, "github")

    try:
        async with httpx.AsyncClient(timeout=12.0) as client:
            token_resp = await client.post(
                "https://github.com/login/oauth/access_token",
                data={
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "code": code,
                    "redirect_uri": redirect_uri,
                },
                headers={"Accept": "application/json"},
            )
            if token_resp.status_code != 200:
                msg = urllib.parse.quote("Gagal menukar kode otentikasi GitHub dengan access token.")
                return RedirectResponse(url=f"/?auth_error={msg}", status_code=status.HTTP_302_FOUND)

            token_data = token_resp.json()
            access_token = token_data.get("access_token")
            if not access_token:
                msg = urllib.parse.quote("Token akses GitHub tidak valid.")
                return RedirectResponse(url=f"/?auth_error={msg}", status_code=status.HTTP_302_FOUND)

            # Ambil email dari GitHub API
            email_resp = await client.get(
                "https://api.github.com/user/emails",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Accept": "application/vnd.github+json",
                },
            )
            email = None
            if email_resp.status_code == 200:
                emails = email_resp.json()
                # Prioritaskan email primary & verified
                primary = [e["email"] for e in emails if e.get("primary") and e.get("verified")]
                if not primary:
                    primary = [e["email"] for e in emails if e.get("verified")]
                if not primary and emails:
                    primary = [emails[0]["email"]]
                email = primary[0] if primary else None
            else:
                user_resp = await client.get(
                    "https://api.github.com/user",
                    headers={"Authorization": f"Bearer {access_token}"},
                )
                if user_resp.status_code == 200:
                    email = user_resp.json().get("email")

        if not email:
            msg = urllib.parse.quote("Tidak dapat mengakses email terverifikasi dari akun GitHub Anda.")
            return RedirectResponse(url=f"/?auth_error={msg}", status_code=status.HTTP_302_FOUND)

        token, is_new = _login_or_register_oauth_user(email=email, db=db, provider="github")
        success_msg = urllib.parse.quote(f"Selamat datang! Berhasil masuk dengan GitHub ({email}).")
        response = RedirectResponse(url=f"/?auth_success={success_msg}", status_code=status.HTTP_302_FOUND)
        response.set_cookie(key="access_token", value=token, httponly=True, samesite="lax")
        return response

    except Exception as exc:
        msg = urllib.parse.quote(f"Terjadi kesalahan saat otentikasi GitHub: {str(exc)}")
        return RedirectResponse(url=f"/?auth_error={msg}", status_code=status.HTTP_302_FOUND)

