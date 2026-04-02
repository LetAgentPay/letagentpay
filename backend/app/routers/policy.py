import uuid

import anthropic
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.dependencies import get_current_account, get_owner_agent
from app.models import Account, PolicyLog
from app.schemas import Policy, PolicyAIRequest, PolicyAIResponse
from app.services.ai_policy import convert_text_to_policy

router = APIRouter(prefix="/api/v1/agents/{agent_id}/policy", tags=["policy"])


@router.get("")
async def get_policy(
    agent_id: str,
    account: Account = Depends(get_current_account),
    db: AsyncSession = Depends(get_db),
):
    agent = await get_owner_agent(agent_id, account, db)
    return {"policy": agent.policy, "policy_text": agent.policy_text}


@router.post("/ai", response_model=PolicyAIResponse)
async def ai_policy_preview(
    agent_id: str,
    body: PolicyAIRequest,
    account: Account = Depends(get_current_account),
    db: AsyncSession = Depends(get_db),
):
    agent = await get_owner_agent(agent_id, account, db)

    if not settings.anthropic_api_key:
        raise HTTPException(
            status_code=503,
            detail="AI policy generation is not configured. Set ANTHROPIC_API_KEY or configure the policy manually via JSON.",
        )

    try:
        result = await convert_text_to_policy(
            message=body.message,
            chat_history=body.chat_history,
            user_timezone=account.timezone,
            current_policy=agent.policy,
        )
    except (ValueError, anthropic.APIError) as e:
        raise HTTPException(
            status_code=422, detail=f"AI could not generate policy: {e}"
        )

    policy_data = result.get("policy", result)
    explanation = result.get("explanation", "")
    summary = result.get("summary", "")

    # Validate through Pydantic
    try:
        Policy(**policy_data)
    except (ValueError, TypeError) as e:
        raise HTTPException(status_code=422, detail=f"AI returned invalid policy: {e}")

    session_id = str(uuid.uuid4())

    # Store policy + summary together so confirm can retrieve the summary
    ai_output = {**policy_data, "_summary": summary}

    # Log the attempt
    log = PolicyLog(
        agent_id=agent.id,
        user_input=body.message,
        ai_output=ai_output,
        accepted=False,
    )
    db.add(log)
    await db.commit()

    return PolicyAIResponse(
        policy_preview=policy_data,
        explanation=explanation,
        session_id=session_id,
    )


@router.post("/ai/confirm")
async def confirm_ai_policy(
    agent_id: str,
    account: Account = Depends(get_current_account),
    db: AsyncSession = Depends(get_db),
):
    agent = await get_owner_agent(agent_id, account, db)

    # Get the latest unconfirmed policy log
    result = await db.execute(
        select(PolicyLog)
        .where(
            PolicyLog.agent_id == agent.id, PolicyLog.accepted == False
        )  # noqa: E712
        .order_by(PolicyLog.created_at.desc())
        .limit(1)
    )
    log = result.scalar_one_or_none()
    if not log:
        raise HTTPException(status_code=400, detail="No pending policy to confirm")

    # Extract policy and summary; _summary is stored alongside policy fields
    ai_output = dict(log.ai_output)
    summary = ai_output.pop("_summary", "")
    policy_data = ai_output

    # Apply policy
    agent.policy = policy_data
    agent.policy_text = summary or log.user_input
    log.accepted = True

    await db.commit()
    return {"message": "Policy confirmed", "policy": agent.policy}


@router.put("")
async def update_policy(
    agent_id: str,
    body: Policy,
    account: Account = Depends(get_current_account),
    db: AsyncSession = Depends(get_db),
):
    agent = await get_owner_agent(agent_id, account, db)
    agent.policy = body.model_dump(exclude_none=True, mode="json")

    await db.commit()
    return {"message": "Policy updated", "policy": agent.policy}
