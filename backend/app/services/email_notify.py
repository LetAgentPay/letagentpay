import asyncio
import logging
from html import escape

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models import Account

logger = logging.getLogger(__name__)


async def send_pending_request_email(
    db: AsyncSession,
    account_id: str,
    agent_name: str,
    amount: str,
    currency: str,
    category: str,
    merchant: str | None,
    request_id: str,
    agent_comment: str | None = None,
    action_tokens=None,
) -> bool:
    """Send email notification about a pending purchase request.

    Returns True if email was sent, False otherwise.
    """
    result = await db.execute(select(Account).where(Account.id == account_id))
    account = result.scalar_one_or_none()
    if not account:
        return False

    safe_name = escape(agent_name)
    safe_amount = escape(amount)
    safe_category = escape(category)
    safe_merchant = escape(merchant) if merchant else None

    safe_currency = escape(currency)
    subject = f"Pending request: {safe_amount} {safe_currency} — {safe_category}"
    safe_comment = escape(agent_comment) if agent_comment else None
    merchant_line = (
        f"<li><strong>Merchant:</strong> {safe_merchant}</li>" if safe_merchant else ""
    )
    comment_line = (
        f"<li><strong>Comment:</strong> {safe_comment}</li>" if safe_comment else ""
    )
    dashboard_url = f"{settings.frontend_url}/dashboard"

    # Build action buttons (interactive approve/reject via action tokens)
    if action_tokens:
        base = f"{settings.frontend_url}/api/v1/requests/action"
        approve_url = f"{base}?token={action_tokens.approve}"
        reject_url = f"{base}?token={action_tokens.reject}"
        action_buttons = f"""\
  <div style="margin: 20px 0;">
    <a href="{approve_url}"
       style="display: inline-block; background: #16a34a; color: #fff; padding: 12px 24px;
              border-radius: 6px; text-decoration: none; font-weight: 500; margin-right: 8px;">
      Approve
    </a>
    <a href="{reject_url}"
       style="display: inline-block; background: #dc2626; color: #fff; padding: 12px 24px;
              border-radius: 6px; text-decoration: none; font-weight: 500;">
      Reject
    </a>
  </div>

  <a href="{dashboard_url}"
     style="display: inline-block; color: #666; padding: 8px 0;
            text-decoration: underline; font-size: 13px;">
    or review in Dashboard
  </a>"""
    else:
        action_buttons = f"""\
  <a href="{dashboard_url}"
     style="display: inline-block; background: #0a0a0a; color: #fff; padding: 12px 24px;
            border-radius: 6px; text-decoration: none; font-weight: 500;">
    Review in Dashboard
  </a>"""

    html = f"""\
<div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; max-width: 480px; margin: 0 auto;">
  <h2 style="margin-bottom: 4px;">New purchase request</h2>
  <p style="color: #666; margin-top: 0;">from <strong>{safe_name}</strong></p>

  <div style="background: #f5f5f5; border-radius: 8px; padding: 16px; margin: 16px 0;">
    <ul style="list-style: none; padding: 0; margin: 0;">
      <li><strong>Amount:</strong> {safe_amount} {safe_currency}</li>
      <li><strong>Category:</strong> {safe_category}</li>
      {merchant_line}
      {comment_line}
    </ul>
  </div>

  <p>This request expires in 30 minutes.</p>

  {action_buttons}

  <p style="color: #999; font-size: 12px; margin-top: 24px;">
    LetAgentPay &mdash; Manage your AI agent spending
  </p>
</div>"""

    if settings.resend_api_key:
        import resend

        resend.api_key = settings.resend_api_key
        try:
            # resend.Emails.send() is synchronous — run in executor
            # to avoid blocking the async event loop
            loop = asyncio.get_running_loop()
            params = {
                "from": settings.email_from,
                "to": [account.email],
                "subject": subject,
                "html": html,
            }
            await loop.run_in_executor(
                None, lambda: resend.Emails.send(params)  # type: ignore[arg-type]
            )
            return True
        except Exception:
            logger.exception(
                "Failed to send pending request email to %s", account.email
            )
            return False
    else:
        logger.info(
            "[DEV] Pending request email for %s: %s %s %s (%s)",
            account.email,
            agent_name,
            amount,
            currency,
            category,
        )
        return False
