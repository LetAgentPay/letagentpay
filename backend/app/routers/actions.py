from html import escape

from fastapi import APIRouter, Depends, Query
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.services.action_tokens import execute_action_token

router = APIRouter(prefix="/api/v1/requests", tags=["actions"])


def _html_page(title: str, message: str, success: bool) -> str:
    color = "#16a34a" if success else "#dc2626"
    icon = "&#10003;" if success else "&#10007;"
    dashboard_url = f"{settings.frontend_url}/dashboard"
    return f"""\
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{escape(title)} — LetAgentPay</title>
  <style>
    body {{
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
      display: flex; justify-content: center; align-items: center;
      min-height: 100vh; margin: 0; background: #fafafa;
    }}
    .card {{
      background: #fff; border-radius: 12px; padding: 40px;
      box-shadow: 0 1px 3px rgba(0,0,0,0.1); text-align: center;
      max-width: 400px; width: 90%;
    }}
    .icon {{
      font-size: 48px; color: {color}; margin-bottom: 16px;
    }}
    h1 {{ font-size: 20px; margin: 0 0 8px; }}
    p {{ color: #666; margin: 0 0 24px; }}
    a {{
      display: inline-block; background: #0a0a0a; color: #fff;
      padding: 10px 20px; border-radius: 6px; text-decoration: none;
      font-weight: 500; font-size: 14px;
    }}
  </style>
</head>
<body>
  <div class="card">
    <div class="icon">{icon}</div>
    <h1>{escape(title)}</h1>
    <p>{escape(message)}</p>
    <a href="{dashboard_url}">Open Dashboard</a>
  </div>
</body>
</html>"""


@router.get("/action")
async def handle_action_token(
    token: str = Query(...),
    db: AsyncSession = Depends(get_db),
) -> HTMLResponse:
    """Execute a one-time action token (approve/reject) from email or Telegram link."""
    result = await execute_action_token(db, token)

    if result.success:
        title = "Request Approved" if result.action == "approve" else "Request Rejected"
        return HTMLResponse(_html_page(title, result.message, success=True))
    else:
        return HTMLResponse(
            _html_page("Action Failed", result.message, success=False),
            status_code=400,
        )
