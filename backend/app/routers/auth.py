import asyncio
import logging
import secrets
from datetime import timedelta

import jwt
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models import Account, VerificationToken
from app.redis import get_redis
from app.schemas import (
    PasswordLoginRequest,
    SendLinkRequest,
    TokenResponse,
    VerifyOtpRequest,
)
from app.services.rate_limit import check_rate_limit
from app.services.telegram import send_admin_notification
from app.utils import ensure_utc, utcnow

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


def _create_access_token(account_id: str, email: str) -> str:
    payload = {
        "sub": account_id,
        "email": email,
        "exp": utcnow() + timedelta(days=settings.access_token_expire_days),
        "iat": utcnow(),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


async def _authenticate_email(email: str, db: AsyncSession, response: Response) -> dict:
    """Find or create account by email, set JWT cookie, return response dict."""
    acc_result = await db.execute(select(Account).where(Account.email == email))
    account = acc_result.scalar_one_or_none()

    is_new = False
    if not account:
        account = Account(email=email)
        db.add(account)
        is_new = True

    # Sync admin flag from ADMIN_EMAILS config
    admin_list = [
        e.strip().lower() for e in settings.admin_emails.split(",") if e.strip()
    ]
    account.is_admin = email in admin_list

    await db.commit()
    await db.refresh(account)

    access_token = _create_access_token(account.id, account.email)

    logger.info("authenticated: account_id=%s email=%s", account.id, email)

    if is_new:
        from app.models import Category

        db.add(Category(account_id=account.id, name="other", display_name="Other"))
        await db.commit()
        asyncio.create_task(send_admin_notification(f"🆕 New user registered: {email}"))

    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        max_age=settings.access_token_expire_days * 86400,
    )
    return {"message": "Authenticated"}


@router.get("/mode")
async def auth_mode():
    """Return current auth mode so the frontend renders the correct form."""
    if settings.self_hosted and settings.admin_password:
        return {"mode": "password"}
    return {"mode": "magic_link"}


@router.post("/login")
async def password_login(
    body: PasswordLoginRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """Password-based login for self-hosted deployments."""
    if not settings.self_hosted or not settings.admin_password:
        raise HTTPException(status_code=404, detail="Not found")

    # Rate limiting
    redis = get_redis()
    ip = request.client.host if request.client else "unknown"
    await check_rate_limit(redis, f"rate_limit:auth:login:{ip}", 10, 900)

    if not secrets.compare_digest(body.password, settings.admin_password):
        logger.warning("password login failed from ip=%s", ip)
        from app.dependencies import _fire_auth_alert

        _fire_auth_alert(f"🔒 Failed password login\nIP: {ip}")
        raise HTTPException(status_code=401, detail="Invalid password")

    email = "admin@localhost"

    # Find or create the default self-hosted account
    acc_result = await db.execute(select(Account).where(Account.email == email))
    account = acc_result.scalar_one_or_none()

    is_new_admin = False
    if not account:
        account = Account(email=email)
        db.add(account)
        is_new_admin = True

    account.is_admin = True

    await db.commit()
    await db.refresh(account)

    if is_new_admin:
        from app.models import Category

        db.add(Category(account_id=account.id, name="other", display_name="Other"))
        await db.commit()

    access_token = _create_access_token(account.id, account.email)

    logger.info("password login: account_id=%s", account.id)

    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        max_age=settings.access_token_expire_days * 86400,
    )
    return {"message": "Logged in"}


@router.post("/send-link", response_model=TokenResponse)
async def send_magic_link(
    body: SendLinkRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Send a magic link and OTP code to the user's email."""
    email = body.email.lower().strip()

    # Rate limiting
    redis = get_redis()
    ip = request.client.host if request.client else "unknown"
    await check_rate_limit(redis, f"rate_limit:auth:send_link:{email}", 5, 900)
    await check_rate_limit(redis, f"rate_limit:auth:send_link:global:{ip}", 20, 900)

    logger.info("send-link for email=%s", email)

    # Generate token and OTP code
    token = secrets.token_urlsafe(32)
    otp_code = str(secrets.randbelow(900000) + 100000)
    expires_at = utcnow() + timedelta(minutes=settings.magic_link_expire_minutes)

    # Remove old tokens for this email
    await db.execute(delete(VerificationToken).where(VerificationToken.email == email))

    # Save new token with OTP
    vt = VerificationToken(
        email=email, token=token, otp_code=otp_code, expires_at=expires_at
    )
    db.add(vt)
    await db.commit()

    # Build magic link URL
    magic_link = f"{settings.magic_link_base_url}?token={token}"

    # Send email via Resend
    if settings.resend_api_key:
        import resend

        resend.api_key = settings.resend_api_key
        resend.Emails.send(
            {
                "from": settings.email_from,
                "to": [email],
                "subject": "Sign in to LetAgentPay",
                "html": (
                    f'<p style="font-size:32px;font-weight:bold;letter-spacing:6px;'
                    f'text-align:center;margin:24px 0">{otp_code}</p>'
                    f"<p>Enter this code in the app, or click the link below:</p>"
                    f'<p><a href="{magic_link}">Sign in to LetAgentPay</a></p>'
                    f"<p>This code expires in {settings.magic_link_expire_minutes} minutes.</p>"
                ),
            }
        )
    else:
        # Dev mode: log code and link since Resend is not configured
        logger.info(
            "Magic link sent to %s (dev mode, email skipped)\n  OTP code: %s\n  Link: %s",
            email,
            otp_code,
            magic_link,
        )

    return TokenResponse(message="Magic link sent to your email")


@router.get("/verify")
async def verify_magic_link(
    token: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Verify magic link token, create account if needed, return JWT."""
    # Rate limiting
    redis = get_redis()
    ip = request.client.host if request.client else "unknown"
    await check_rate_limit(redis, f"rate_limit:auth:verify:{ip}", 10, 900)

    result = await db.execute(
        select(VerificationToken).where(VerificationToken.token == token)
    )
    vt = result.scalar_one_or_none()

    if not vt:
        logger.warning("verify: token not found (token=%s...)", token[:8])
        raise HTTPException(status_code=400, detail="Invalid or expired token")

    now = utcnow()
    if ensure_utc(vt.expires_at) < now:
        logger.warning("verify: token expired for email=%s", vt.email)
        await db.delete(vt)
        await db.commit()
        raise HTTPException(status_code=400, detail="Token expired")

    email = vt.email

    # Delete used token
    await db.delete(vt)

    # Redirect to dashboard — called by Next.js Route Handler server-side,
    # which forwards the Set-Cookie to the browser.
    resp = RedirectResponse(url=f"{settings.frontend_url}/dashboard", status_code=302)
    await _authenticate_email(email, db, resp)
    return resp


@router.post("/verify-otp")
async def verify_otp(
    body: VerifyOtpRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """Verify OTP code from email, create account if needed, set JWT cookie."""
    # Rate limiting
    redis = get_redis()
    ip = request.client.host if request.client else "unknown"
    await check_rate_limit(redis, f"rate_limit:auth:verify_otp:{ip}", 10, 900)

    email = body.email.lower().strip()
    await check_rate_limit(redis, f"rate_limit:auth:verify_otp:{email}", 10, 900)

    result = await db.execute(
        select(VerificationToken).where(VerificationToken.email == email)
    )
    vt = result.scalar_one_or_none()

    if not vt:
        raise HTTPException(status_code=400, detail="Invalid or expired code")

    if ensure_utc(vt.expires_at) < utcnow():
        await db.delete(vt)
        await db.commit()
        raise HTTPException(status_code=400, detail="Code expired")

    if vt.otp_attempts >= 5:
        await db.delete(vt)
        await db.commit()
        raise HTTPException(
            status_code=400, detail="Too many attempts, request a new code"
        )

    if not vt.otp_code or not secrets.compare_digest(body.code, vt.otp_code):
        vt.otp_attempts += 1
        await db.commit()
        raise HTTPException(status_code=400, detail="Invalid code")

    # OTP valid — delete token and authenticate
    await db.delete(vt)
    return await _authenticate_email(email, db, response)


@router.post("/logout")
async def logout(response: Response):
    """Clear auth cookie."""
    response.delete_cookie("access_token")
    return {"message": "Logged out"}
