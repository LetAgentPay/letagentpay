from datetime import timedelta
from unittest.mock import patch

from sqlalchemy import select

from app.config import settings
from app.models import Account, VerificationToken
from app.utils import utcnow


class TestSendLink:
    async def test_send_link_creates_token(self, client, db):
        resp = await client.post(
            "/api/v1/auth/send-link", json={"email": "new@example.com"}
        )
        assert resp.status_code == 200
        assert resp.json()["message"] == "Magic link sent to your email"

        result = await db.execute(
            select(VerificationToken).where(
                VerificationToken.email == "new@example.com"
            )
        )
        token = result.scalar_one()
        assert token is not None
        assert token.expires_at > utcnow()

    async def test_send_link_generates_otp(self, client, db):
        await client.post("/api/v1/auth/send-link", json={"email": "otp@example.com"})

        result = await db.execute(
            select(VerificationToken).where(
                VerificationToken.email == "otp@example.com"
            )
        )
        token = result.scalar_one()
        assert token.otp_code is not None
        assert len(token.otp_code) == 6
        assert token.otp_code.isdigit()

    async def test_send_link_rejects_invalid_email(self, client, db):
        """Garbage must be rejected by the schema, not by Resend at send time."""
        for bad in ["not-an-email", "no@tld", "a b@example.com", "", "@example.com"]:
            resp = await client.post("/api/v1/auth/send-link", json={"email": bad})
            assert resp.status_code == 422, bad

        # And nothing was committed to the DB on the way
        result = await db.execute(select(VerificationToken))
        assert result.scalars().all() == []

    async def test_send_link_replaces_old_tokens(self, client, db):
        await client.post("/api/v1/auth/send-link", json={"email": "dup@example.com"})
        await client.post("/api/v1/auth/send-link", json={"email": "dup@example.com"})

        result = await db.execute(
            select(VerificationToken).where(
                VerificationToken.email == "dup@example.com"
            )
        )
        tokens = result.scalars().all()
        assert len(tokens) == 1

    async def test_send_link_normalizes_email(self, client, db):
        await client.post(
            "/api/v1/auth/send-link", json={"email": "  TEST@Example.COM  "}
        )

        result = await db.execute(
            select(VerificationToken).where(
                VerificationToken.email == "test@example.com"
            )
        )
        assert result.scalar_one() is not None


class TestVerify:
    async def test_verify_creates_account_and_sets_cookie(self, client, db):
        # Create token
        await client.post(
            "/api/v1/auth/send-link", json={"email": "verify@example.com"}
        )
        result = await db.execute(
            select(VerificationToken).where(
                VerificationToken.email == "verify@example.com"
            )
        )
        vt = result.scalar_one()

        # Verify — returns 302 redirect with cookie
        resp = await client.get(
            f"/api/v1/auth/verify?token={vt.token}", follow_redirects=False
        )
        assert resp.status_code == 302
        assert "/dashboard" in resp.headers["location"]

        # Account created
        result = await db.execute(
            select(Account).where(Account.email == "verify@example.com")
        )
        account = result.scalar_one()
        assert account is not None
        assert account.plan == "free"

        # Cookie set
        assert "access_token" in resp.cookies

    async def test_verify_existing_account(self, client, db, account):
        await client.post("/api/v1/auth/send-link", json={"email": account.email})
        result = await db.execute(
            select(VerificationToken).where(VerificationToken.email == account.email)
        )
        vt = result.scalar_one()

        resp = await client.get(
            f"/api/v1/auth/verify?token={vt.token}", follow_redirects=False
        )
        assert resp.status_code == 302
        assert "access_token" in resp.cookies

    async def test_verify_invalid_token(self, client):
        resp = await client.get("/api/v1/auth/verify?token=invalid-token")
        assert resp.status_code == 400

    async def test_verify_expired_token(self, client, db):
        vt = VerificationToken(
            email="expired@example.com",
            token="expired-token-123",
            expires_at=utcnow() - timedelta(minutes=1),
        )
        db.add(vt)
        await db.commit()

        resp = await client.get("/api/v1/auth/verify?token=expired-token-123")
        assert resp.status_code == 400
        assert "expired" in resp.json()["detail"].lower()

    async def test_verify_deletes_used_token(self, client, db):
        await client.post("/api/v1/auth/send-link", json={"email": "once@example.com"})
        result = await db.execute(
            select(VerificationToken).where(
                VerificationToken.email == "once@example.com"
            )
        )
        vt = result.scalar_one()
        token_value = vt.token

        await client.get(f"/api/v1/auth/verify?token={token_value}")

        # Token should be deleted
        result = await db.execute(
            select(VerificationToken).where(VerificationToken.token == token_value)
        )
        assert result.scalar_one_or_none() is None


class TestVerifyOtp:
    async def _send_and_get_otp(self, client, db, email="otp@example.com"):
        await client.post("/api/v1/auth/send-link", json={"email": email})
        result = await db.execute(
            select(VerificationToken).where(VerificationToken.email == email)
        )
        vt = result.scalar_one()
        return vt.otp_code

    async def test_verify_otp_success(self, client, db):
        otp = await self._send_and_get_otp(client, db)

        resp = await client.post(
            "/api/v1/auth/verify-otp",
            json={"email": "otp@example.com", "code": otp},
        )
        assert resp.status_code == 200
        assert "access_token" in resp.cookies

        # Account created
        result = await db.execute(
            select(Account).where(Account.email == "otp@example.com")
        )
        assert result.scalar_one() is not None

    async def test_verify_otp_deletes_token(self, client, db):
        otp = await self._send_and_get_otp(client, db)

        await client.post(
            "/api/v1/auth/verify-otp",
            json={"email": "otp@example.com", "code": otp},
        )

        result = await db.execute(
            select(VerificationToken).where(
                VerificationToken.email == "otp@example.com"
            )
        )
        assert result.scalar_one_or_none() is None

    async def test_verify_otp_wrong_code(self, client, db):
        await self._send_and_get_otp(client, db)

        resp = await client.post(
            "/api/v1/auth/verify-otp",
            json={"email": "otp@example.com", "code": "000000"},
        )
        assert resp.status_code == 400
        assert "invalid code" in resp.json()["detail"].lower()

        # Token still exists with incremented attempts
        result = await db.execute(
            select(VerificationToken).where(
                VerificationToken.email == "otp@example.com"
            )
        )
        vt = result.scalar_one()
        assert vt.otp_attempts == 1

    async def test_verify_otp_max_attempts(self, client, db):
        await self._send_and_get_otp(client, db)

        # Send 5 wrong attempts
        for _ in range(5):
            await client.post(
                "/api/v1/auth/verify-otp",
                json={"email": "otp@example.com", "code": "000000"},
            )

        # 6th attempt should say too many attempts
        resp = await client.post(
            "/api/v1/auth/verify-otp",
            json={"email": "otp@example.com", "code": "000000"},
        )
        assert resp.status_code == 400
        assert "too many attempts" in resp.json()["detail"].lower()

        # Token deleted
        result = await db.execute(
            select(VerificationToken).where(
                VerificationToken.email == "otp@example.com"
            )
        )
        assert result.scalar_one_or_none() is None

    async def test_verify_otp_expired(self, client, db):
        vt = VerificationToken(
            email="expired-otp@example.com",
            token="some-token-123",
            otp_code="123456",
            expires_at=utcnow() - timedelta(minutes=1),
        )
        db.add(vt)
        await db.commit()

        resp = await client.post(
            "/api/v1/auth/verify-otp",
            json={"email": "expired-otp@example.com", "code": "123456"},
        )
        assert resp.status_code == 400
        assert "expired" in resp.json()["detail"].lower()

    async def test_verify_otp_no_token(self, client):
        resp = await client.post(
            "/api/v1/auth/verify-otp",
            json={"email": "unknown@example.com", "code": "123456"},
        )
        assert resp.status_code == 400

    async def test_verify_otp_existing_account(self, client, db, account):
        otp = await self._send_and_get_otp(client, db, email=account.email)

        resp = await client.post(
            "/api/v1/auth/verify-otp",
            json={"email": account.email, "code": otp},
        )
        assert resp.status_code == 200
        assert "access_token" in resp.cookies

    async def test_verify_otp_normalizes_email(self, client, db):
        otp = await self._send_and_get_otp(client, db, email="norm@example.com")

        resp = await client.post(
            "/api/v1/auth/verify-otp",
            json={"email": "  NORM@Example.COM  ", "code": otp},
        )
        assert resp.status_code == 200

    async def test_verify_otp_invalid_format(self, client):
        resp = await client.post(
            "/api/v1/auth/verify-otp",
            json={"email": "test@example.com", "code": "abc"},
        )
        assert resp.status_code == 422

    async def test_magic_link_invalidates_otp(self, client, db):
        """Using magic link should also delete the OTP (same token row)."""
        await self._send_and_get_otp(client, db, email="both@example.com")

        # Get the token value for magic link
        result = await db.execute(
            select(VerificationToken).where(
                VerificationToken.email == "both@example.com"
            )
        )
        vt = result.scalar_one()
        otp = vt.otp_code
        token = vt.token

        # Use magic link
        await client.get(f"/api/v1/auth/verify?token={token}")

        # OTP should no longer work
        resp = await client.post(
            "/api/v1/auth/verify-otp",
            json={"email": "both@example.com", "code": otp},
        )
        assert resp.status_code == 400


class TestAuthMode:
    async def test_auth_mode_magic_link_by_default(self, client):
        resp = await client.get("/api/v1/auth/mode")
        assert resp.status_code == 200
        assert resp.json()["mode"] == "magic_link"

    async def test_auth_mode_password_when_self_hosted(self, client):
        with (
            patch.object(settings, "self_hosted", True),
            patch.object(settings, "admin_password", "test-pass"),
        ):
            resp = await client.get("/api/v1/auth/mode")
        assert resp.status_code == 200
        assert resp.json()["mode"] == "password"


class TestPasswordLogin:
    async def test_login_success(self, client, db):
        with (
            patch.object(settings, "self_hosted", True),
            patch.object(settings, "admin_password", "correct-pass"),
        ):
            resp = await client.post(
                "/api/v1/auth/login", json={"password": "correct-pass"}
            )
        assert resp.status_code == 200
        assert "access_token" in resp.cookies

        # Account created as admin
        result = await db.execute(
            select(Account).where(Account.email == "admin@localhost")
        )
        account = result.scalar_one()
        assert account.is_admin is True

    async def test_login_wrong_password(self, client):
        with (
            patch.object(settings, "self_hosted", True),
            patch.object(settings, "admin_password", "correct-pass"),
        ):
            resp = await client.post(
                "/api/v1/auth/login", json={"password": "wrong-pass"}
            )
        assert resp.status_code == 401

    async def test_login_disabled_when_not_self_hosted(self, client):
        resp = await client.post("/api/v1/auth/login", json={"password": "any-pass"})
        assert resp.status_code == 404

    async def test_login_reuses_existing_account(self, client, db):
        # Create account beforehand
        acc = Account(email="admin@localhost")
        db.add(acc)
        await db.commit()

        with (
            patch.object(settings, "self_hosted", True),
            patch.object(settings, "admin_password", "pass123"),
        ):
            resp = await client.post("/api/v1/auth/login", json={"password": "pass123"})
        assert resp.status_code == 200

        # Should not create a duplicate
        result = await db.execute(
            select(Account).where(Account.email == "admin@localhost")
        )
        accounts = result.scalars().all()
        assert len(accounts) == 1


class TestSlidingSession:
    async def test_fresh_token_not_refreshed(self, auth_client):
        """Token with >50% lifetime remaining should NOT be refreshed."""
        resp = await auth_client.get("/api/v1/me")
        assert resp.status_code == 200
        # No new Set-Cookie header (token is fresh)
        assert "set-cookie" not in resp.headers

    async def test_old_token_gets_refreshed(self, client, account):
        """Token with >50% lifetime elapsed should be refreshed."""
        import jwt as pyjwt

        # Create a token issued 5 days ago (>50% of 7-day lifetime)
        iat = utcnow() - timedelta(days=5)
        payload = {
            "sub": account.id,
            "email": account.email,
            "iat": iat,
            "exp": iat + timedelta(days=settings.access_token_expire_days),
        }
        old_token = pyjwt.encode(
            payload, settings.jwt_secret, algorithm=settings.jwt_algorithm
        )
        client.cookies.set("access_token", old_token)

        resp = await client.get("/api/v1/me")
        assert resp.status_code == 200
        # Should get a refreshed cookie
        assert "set-cookie" in resp.headers
        assert "access_token" in resp.headers["set-cookie"]

        client.cookies.clear()


class TestLogout:
    async def test_logout_clears_cookie(self, client):
        resp = await client.post("/api/v1/auth/logout")
        assert resp.status_code == 200
        assert resp.json()["message"] == "Logged out"
