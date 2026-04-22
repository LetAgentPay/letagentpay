import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.dependencies import get_current_account
from app.models import Account, Category, CategoryAlias, PurchaseRequest
from app.schemas import (
    CategoryAliasCreate,
    CategoryAliasResponse,
    CategoryCreate,
    CategoryResponse,
    CategoryUpdate,
    ResolveOrphanRequest,
)
from app.services.category_resolver import (
    DEFAULT_CATEGORIES,
    DEFAULT_CATEGORY_ALIASES,
    _normalize,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/me/categories", tags=["categories"])


def _category_response(cat: Category) -> CategoryResponse:
    return CategoryResponse(
        id=cat.id,
        name=cat.name,
        display_name=cat.display_name,
        is_active=cat.is_active,
        aliases=[
            CategoryAliasResponse(
                id=a.id,
                alias=a.alias,
                is_auto_generated=a.is_auto_generated,
                created_at=a.created_at,
            )
            for a in cat.aliases
        ],
        created_at=cat.created_at,
    )


@router.get("", response_model=list[CategoryResponse])
async def list_categories(
    account: Account = Depends(get_current_account),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Category)
        .options(selectinload(Category.aliases))
        .where(Category.account_id == account.id)
        .order_by(Category.name)
    )
    return [_category_response(c) for c in result.scalars().all()]


@router.post("", response_model=CategoryResponse, status_code=201)
async def create_category(
    body: CategoryCreate,
    account: Account = Depends(get_current_account),
    db: AsyncSession = Depends(get_db),
):
    # Check uniqueness
    existing = await db.execute(
        select(Category).where(
            Category.account_id == account.id, Category.name == body.name
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=409, detail=f"Category '{body.name}' already exists"
        )

    cat = Category(
        account_id=account.id,
        name=body.name,
        display_name=body.display_name,
    )
    db.add(cat)
    await db.commit()
    await db.refresh(cat, attribute_names=["aliases"])

    return _category_response(cat)


@router.put("/{category_id}", response_model=CategoryResponse)
async def update_category(
    category_id: str,
    body: CategoryUpdate,
    account: Account = Depends(get_current_account),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Category)
        .options(selectinload(Category.aliases))
        .where(Category.id == category_id, Category.account_id == account.id)
    )
    cat = result.scalar_one_or_none()
    if not cat:
        raise HTTPException(status_code=404, detail="Category not found")

    if body.is_active is False and cat.name == "other":
        raise HTTPException(
            status_code=400, detail="Cannot deactivate 'other' category"
        )

    if body.display_name is not None:
        cat.display_name = body.display_name
    if body.is_active is not None:
        cat.is_active = body.is_active

    await db.commit()
    await db.refresh(cat, attribute_names=["aliases"])

    return _category_response(cat)


@router.delete("/{category_id}", status_code=204)
async def delete_category(
    category_id: str,
    account: Account = Depends(get_current_account),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Category).where(
            Category.id == category_id, Category.account_id == account.id
        )
    )
    cat = result.scalar_one_or_none()
    if not cat:
        raise HTTPException(status_code=404, detail="Category not found")
    if cat.name == "other":
        raise HTTPException(status_code=400, detail="Cannot delete 'other' category")

    await db.delete(cat)
    await db.commit()


# ---------------------------------------------------------------------------
# Aliases
# ---------------------------------------------------------------------------


@router.post(
    "/{category_id}/aliases", response_model=CategoryAliasResponse, status_code=201
)
async def add_alias(
    category_id: str,
    body: CategoryAliasCreate,
    account: Account = Depends(get_current_account),
    db: AsyncSession = Depends(get_db),
):
    # Verify category belongs to account
    result = await db.execute(
        select(Category).where(
            Category.id == category_id, Category.account_id == account.id
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Category not found")

    normalized = _normalize(body.alias)
    if not normalized:
        raise HTTPException(status_code=400, detail="Alias cannot be empty")

    # Check uniqueness across all aliases in account
    existing = await db.execute(
        select(CategoryAlias).where(
            CategoryAlias.account_id == account.id, CategoryAlias.alias == normalized
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=409,
            detail=f"Alias '{normalized}' already exists in this account",
        )

    alias = CategoryAlias(
        account_id=account.id,
        category_id=category_id,
        alias=normalized,
    )
    db.add(alias)
    await db.commit()
    await db.refresh(alias)

    return CategoryAliasResponse(
        id=alias.id,
        alias=alias.alias,
        is_auto_generated=alias.is_auto_generated,
        created_at=alias.created_at,
    )


@router.delete("/{category_id}/aliases/{alias_id}", status_code=204)
async def remove_alias(
    category_id: str,
    alias_id: str,
    account: Account = Depends(get_current_account),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(CategoryAlias).where(
            CategoryAlias.id == alias_id,
            CategoryAlias.category_id == category_id,
            CategoryAlias.account_id == account.id,
        )
    )
    alias = result.scalar_one_or_none()
    if not alias:
        raise HTTPException(status_code=404, detail="Alias not found")

    await db.delete(alias)
    await db.commit()


# ---------------------------------------------------------------------------
# Import defaults
# ---------------------------------------------------------------------------


@router.post("/import-defaults", response_model=list[CategoryResponse])
async def import_defaults(
    account: Account = Depends(get_current_account),
    db: AsyncSession = Depends(get_db),
):
    """Import default 16 categories and 137 aliases. Idempotent — skips existing."""
    # Load existing categories and aliases
    existing_cats_result = await db.execute(
        select(Category).where(Category.account_id == account.id)
    )
    existing_cats = {c.name: c for c in existing_cats_result.scalars().all()}

    existing_aliases_result = await db.execute(
        select(CategoryAlias.alias).where(CategoryAlias.account_id == account.id)
    )
    existing_alias_set = {row[0] for row in existing_aliases_result.all()}

    created = []
    # Create missing categories
    for cat_name in sorted(DEFAULT_CATEGORIES):
        if cat_name not in existing_cats:
            cat = Category(
                account_id=account.id,
                name=cat_name,
                display_name=cat_name.replace("_", " ").title(),
            )
            db.add(cat)
            existing_cats[cat_name] = cat
            created.append(cat)

    await db.flush()  # Ensure IDs are assigned

    # Create missing aliases
    for alias_name, target_cat in DEFAULT_CATEGORY_ALIASES.items():
        if alias_name not in existing_alias_set and target_cat in existing_cats:
            alias = CategoryAlias(
                account_id=account.id,
                category_id=existing_cats[target_cat].id,
                alias=alias_name,
            )
            db.add(alias)

    await db.commit()

    # Return all categories with aliases
    result = await db.execute(
        select(Category)
        .options(selectinload(Category.aliases))
        .where(Category.account_id == account.id)
        .order_by(Category.name)
    )
    return [_category_response(c) for c in result.scalars().all()]


# ---------------------------------------------------------------------------
# Generate aliases (LLM)
# ---------------------------------------------------------------------------


@router.post(
    "/{category_id}/generate-aliases", response_model=list[CategoryAliasResponse]
)
async def generate_aliases_endpoint(
    category_id: str,
    account: Account = Depends(get_current_account),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Category)
        .options(selectinload(Category.aliases))
        .where(Category.id == category_id, Category.account_id == account.id)
    )
    cat = result.scalar_one_or_none()
    if not cat:
        raise HTTPException(status_code=404, detail="Category not found")

    # Get all existing aliases for this account (to avoid collisions)
    all_aliases_result = await db.execute(
        select(CategoryAlias.alias).where(CategoryAlias.account_id == account.id)
    )
    existing_aliases = {row[0] for row in all_aliases_result.all()}

    # Also exclude all category names in this account
    all_cats_result = await db.execute(
        select(Category.name).where(Category.account_id == account.id)
    )
    existing_aliases |= {row[0] for row in all_cats_result.all()}

    from app.services.category_alias_generator import generate_aliases

    suggestions = await generate_aliases(cat.name, cat.display_name, existing_aliases)

    created = []
    for alias_text in suggestions:
        normalized = _normalize(alias_text)
        if normalized and normalized not in existing_aliases:
            alias = CategoryAlias(
                account_id=account.id,
                category_id=cat.id,
                alias=normalized,
                is_auto_generated=True,
            )
            db.add(alias)
            existing_aliases.add(normalized)
            created.append(alias)

    await db.commit()
    for a in created:
        await db.refresh(a)

    return [
        CategoryAliasResponse(
            id=a.id,
            alias=a.alias,
            is_auto_generated=a.is_auto_generated,
            created_at=a.created_at,
        )
        for a in created
    ]


# ---------------------------------------------------------------------------
# Resolve orphan categories
# ---------------------------------------------------------------------------


@router.post("/resolve-orphan")
async def resolve_orphan(
    body: ResolveOrphanRequest,
    account: Account = Depends(get_current_account),
    db: AsyncSession = Depends(get_db),
):
    """Map an unresolved category to an existing category, optionally creating an alias."""
    # Verify target category belongs to account
    result = await db.execute(
        select(Category).where(
            Category.id == body.category_id, Category.account_id == account.id
        )
    )
    cat = result.scalar_one_or_none()
    if not cat:
        raise HTTPException(status_code=404, detail="Target category not found")

    normalized_raw = _normalize(body.raw_category)

    # Optionally create alias for future auto-resolution
    if body.create_alias and normalized_raw:
        existing = await db.execute(
            select(CategoryAlias).where(
                CategoryAlias.account_id == account.id,
                CategoryAlias.alias == normalized_raw,
            )
        )
        if not existing.scalar_one_or_none():
            alias = CategoryAlias(
                account_id=account.id,
                category_id=cat.id,
                alias=normalized_raw,
            )
            db.add(alias)

    # Update all unresolved purchase requests with this raw_category for this account
    # Need to join through agents to filter by account
    from app.models import Agent

    agent_ids_result = await db.execute(
        select(Agent.id).where(Agent.account_id == account.id)
    )
    agent_ids = [row[0] for row in agent_ids_result.all()]

    if agent_ids:
        await db.execute(
            update(PurchaseRequest)
            .where(
                PurchaseRequest.agent_id.in_(agent_ids),
                PurchaseRequest.category_status == "unresolved",
                PurchaseRequest.original_category == body.raw_category,
            )
            .values(category=cat.name, category_status=None)
        )

    await db.commit()

    return {"resolved": True, "category": cat.name}
