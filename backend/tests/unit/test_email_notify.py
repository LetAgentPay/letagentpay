"""Tests for email notification service."""

from unittest.mock import MagicMock, patch

from app.services.email_notify import send_pending_request_email


class TestSendPendingRequestEmail:
    async def test_html_escape_applied(self, db, account):
        """Verify that user data is HTML-escaped in the email body."""
        with patch("app.services.email_notify.settings") as mock_settings:
            mock_settings.resend_api_key = "test-key"
            mock_settings.email_from = "test@letagentpay.com"
            mock_settings.frontend_url = "http://localhost:3000"

            mock_resend = MagicMock()
            mock_resend.Emails.send = MagicMock()

            with patch.dict("sys.modules", {"resend": mock_resend}):
                result = await send_pending_request_email(
                    db=db,
                    account_id=account.id,
                    agent_name='<script>alert("xss")</script>',
                    amount="100.00",
                    currency="USD",
                    category="groceries",
                    merchant='<img src=x onerror="hack()">',
                    request_id="req-1",
                )

            assert result is True
            call_args = mock_resend.Emails.send.call_args[0][0]
            html = call_args["html"]
            assert "<script>" not in html
            assert "&lt;script&gt;" in html
            assert "<img src=x" not in html
            assert "&lt;img src=x" in html

    async def test_email_sent_when_resend_configured(self, db, account):
        """Email is sent when resend_api_key is set."""
        with patch("app.services.email_notify.settings") as mock_settings:
            mock_settings.resend_api_key = "re_test_key"
            mock_settings.email_from = "test@letagentpay.com"
            mock_settings.frontend_url = "http://localhost:3000"

            mock_resend = MagicMock()
            mock_resend.Emails.send = MagicMock()

            with patch.dict("sys.modules", {"resend": mock_resend}):
                result = await send_pending_request_email(
                    db=db,
                    account_id=account.id,
                    agent_name="Test Agent",
                    amount="50.00",
                    currency="USD",
                    category="food",
                    merchant="Store",
                    request_id="req-2",
                )

            assert result is True
            mock_resend.Emails.send.assert_called_once()
            call_args = mock_resend.Emails.send.call_args[0][0]
            assert call_args["to"] == [account.email]
            assert "50.00" in call_args["subject"]

    async def test_returns_false_when_resend_not_configured(self, db, account):
        """Returns False when resend_api_key is empty."""
        with patch("app.services.email_notify.settings") as mock_settings:
            mock_settings.resend_api_key = ""

            result = await send_pending_request_email(
                db=db,
                account_id=account.id,
                agent_name="Agent",
                amount="10.00",
                currency="USD",
                category="misc",
                merchant=None,
                request_id="req-3",
            )

        assert result is False

    async def test_returns_false_when_account_not_found(self, db):
        """Returns False when account_id does not exist."""
        result = await send_pending_request_email(
            db=db,
            account_id="nonexistent-id",
            agent_name="Agent",
            amount="10.00",
            currency="USD",
            category="misc",
            merchant=None,
            request_id="req-4",
        )
        assert result is False

    async def test_returns_false_on_resend_exception(self, db, account):
        """Returns False when resend raises an exception."""
        with patch("app.services.email_notify.settings") as mock_settings:
            mock_settings.resend_api_key = "re_test_key"
            mock_settings.email_from = "test@letagentpay.com"
            mock_settings.frontend_url = "http://localhost:3000"

            mock_resend = MagicMock()
            mock_resend.Emails.send = MagicMock(side_effect=Exception("API error"))

            with patch.dict("sys.modules", {"resend": mock_resend}):
                result = await send_pending_request_email(
                    db=db,
                    account_id=account.id,
                    agent_name="Agent",
                    amount="10.00",
                    currency="USD",
                    category="misc",
                    merchant=None,
                    request_id="req-5",
                )

            assert result is False

    async def test_email_includes_agent_comment(self, db, account):
        """Agent comment is included and HTML-escaped in the email body."""
        with patch("app.services.email_notify.settings") as mock_settings:
            mock_settings.resend_api_key = "re_test_key"
            mock_settings.email_from = "test@letagentpay.com"
            mock_settings.frontend_url = "http://localhost:3000"

            mock_resend = MagicMock()
            mock_resend.Emails.send = MagicMock()

            with patch.dict("sys.modules", {"resend": mock_resend}):
                result = await send_pending_request_email(
                    db=db,
                    account_id=account.id,
                    agent_name="Test Agent",
                    amount="75.00",
                    currency="USD",
                    category="groceries",
                    merchant="FreshMart",
                    request_id="req-comment-1",
                    agent_comment="Need this for <b>tonight</b>",
                )

            assert result is True
            call_args = mock_resend.Emails.send.call_args[0][0]
            html = call_args["html"]
            # Comment should be present and escaped
            assert "Need this for &lt;b&gt;tonight&lt;/b&gt;" in html
            assert "<b>tonight</b>" not in html
            assert "<strong>Comment:</strong>" in html

    async def test_email_no_comment_line_when_none(self, db, account):
        """When agent_comment is None, no Comment line appears in email."""
        with patch("app.services.email_notify.settings") as mock_settings:
            mock_settings.resend_api_key = "re_test_key"
            mock_settings.email_from = "test@letagentpay.com"
            mock_settings.frontend_url = "http://localhost:3000"

            mock_resend = MagicMock()
            mock_resend.Emails.send = MagicMock()

            with patch.dict("sys.modules", {"resend": mock_resend}):
                result = await send_pending_request_email(
                    db=db,
                    account_id=account.id,
                    agent_name="Test Agent",
                    amount="25.00",
                    currency="USD",
                    category="food",
                    merchant="Cafe",
                    request_id="req-no-comment",
                    agent_comment=None,
                )

            assert result is True
            call_args = mock_resend.Emails.send.call_args[0][0]
            html = call_args["html"]
            assert "Comment:" not in html
