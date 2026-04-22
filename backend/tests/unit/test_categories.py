from sqlalchemy import select

from app.models import Category, CategoryAlias


class TestListCategories:
    async def test_list_categories(self, auth_client, account):
        resp = await auth_client.get("/api/v1/me/categories")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) > 0
        names = {c["name"] for c in data}
        assert "other" in names
        assert "groceries" in names

    async def test_list_categories_unauthorized(self, client):
        resp = await client.get("/api/v1/me/categories")
        assert resp.status_code == 401


class TestCreateCategory:
    async def test_create_category(self, auth_client, account):
        resp = await auth_client.post(
            "/api/v1/me/categories",
            json={"name": "api_costs", "display_name": "API Costs"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "api_costs"
        assert data["display_name"] == "API Costs"
        assert data["is_active"] is True
        assert data["aliases"] == []

    async def test_create_duplicate_category(self, auth_client, account):
        resp = await auth_client.post(
            "/api/v1/me/categories",
            json={"name": "other"},
        )
        assert resp.status_code == 409

    async def test_create_category_invalid_name(self, auth_client, account):
        resp = await auth_client.post(
            "/api/v1/me/categories",
            json={"name": "Invalid Name!"},
        )
        assert resp.status_code == 422

    async def test_create_category_uppercase_rejected(self, auth_client, account):
        resp = await auth_client.post(
            "/api/v1/me/categories",
            json={"name": "MyCategory"},
        )
        assert resp.status_code == 422


class TestUpdateCategory:
    async def test_update_display_name(self, auth_client, account, db):
        cat = await db.execute(
            select(Category).where(
                Category.account_id == account.id, Category.name == "groceries"
            )
        )
        cat_obj = cat.scalar_one()
        resp = await auth_client.put(
            f"/api/v1/me/categories/{cat_obj.id}",
            json={"display_name": "Fresh Groceries"},
        )
        assert resp.status_code == 200
        assert resp.json()["display_name"] == "Fresh Groceries"

    async def test_deactivate_category(self, auth_client, account, db):
        cat = await db.execute(
            select(Category).where(
                Category.account_id == account.id, Category.name == "groceries"
            )
        )
        cat_obj = cat.scalar_one()
        resp = await auth_client.put(
            f"/api/v1/me/categories/{cat_obj.id}",
            json={"is_active": False},
        )
        assert resp.status_code == 200
        assert resp.json()["is_active"] is False

    async def test_cannot_deactivate_other(self, auth_client, account, db):
        cat = await db.execute(
            select(Category).where(
                Category.account_id == account.id, Category.name == "other"
            )
        )
        cat_obj = cat.scalar_one()
        resp = await auth_client.put(
            f"/api/v1/me/categories/{cat_obj.id}",
            json={"is_active": False},
        )
        assert resp.status_code == 400

    async def test_update_nonexistent(self, auth_client, account):
        resp = await auth_client.put(
            "/api/v1/me/categories/nonexistent-id",
            json={"display_name": "X"},
        )
        assert resp.status_code == 404


class TestDeleteCategory:
    async def test_delete_category(self, auth_client, account, db):
        # Create a throwaway category
        resp = await auth_client.post(
            "/api/v1/me/categories",
            json={"name": "throwaway"},
        )
        cat_id = resp.json()["id"]

        resp = await auth_client.delete(f"/api/v1/me/categories/{cat_id}")
        assert resp.status_code == 204

        # Verify deleted
        result = await db.execute(select(Category).where(Category.id == cat_id))
        assert result.scalar_one_or_none() is None

    async def test_cannot_delete_other(self, auth_client, account, db):
        cat = await db.execute(
            select(Category).where(
                Category.account_id == account.id, Category.name == "other"
            )
        )
        cat_obj = cat.scalar_one()
        resp = await auth_client.delete(f"/api/v1/me/categories/{cat_obj.id}")
        assert resp.status_code == 400

    async def test_delete_nonexistent(self, auth_client, account):
        resp = await auth_client.delete("/api/v1/me/categories/nonexistent-id")
        assert resp.status_code == 404


class TestCategoryAliases:
    async def test_add_alias(self, auth_client, account, db):
        cat = await db.execute(
            select(Category).where(
                Category.account_id == account.id, Category.name == "electronics"
            )
        )
        cat_obj = cat.scalar_one()
        resp = await auth_client.post(
            f"/api/v1/me/categories/{cat_obj.id}/aliases",
            json={"alias": "gadgets"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["alias"] == "gadgets"
        assert data["is_auto_generated"] is False

    async def test_add_duplicate_alias(self, auth_client, account, db):
        # "food" alias already exists in conftest
        cat = await db.execute(
            select(Category).where(
                Category.account_id == account.id, Category.name == "electronics"
            )
        )
        cat_obj = cat.scalar_one()
        resp = await auth_client.post(
            f"/api/v1/me/categories/{cat_obj.id}/aliases",
            json={"alias": "food"},
        )
        assert resp.status_code == 409

    async def test_remove_alias(self, auth_client, account, db):
        # Create alias first
        cat = await db.execute(
            select(Category).where(
                Category.account_id == account.id, Category.name == "electronics"
            )
        )
        cat_obj = cat.scalar_one()
        resp = await auth_client.post(
            f"/api/v1/me/categories/{cat_obj.id}/aliases",
            json={"alias": "tech_stuff"},
        )
        alias_id = resp.json()["id"]

        resp = await auth_client.delete(
            f"/api/v1/me/categories/{cat_obj.id}/aliases/{alias_id}"
        )
        assert resp.status_code == 204

    async def test_remove_nonexistent_alias(self, auth_client, account, db):
        cat = await db.execute(
            select(Category).where(
                Category.account_id == account.id, Category.name == "electronics"
            )
        )
        cat_obj = cat.scalar_one()
        resp = await auth_client.delete(
            f"/api/v1/me/categories/{cat_obj.id}/aliases/nonexistent-id"
        )
        assert resp.status_code == 404


class TestImportDefaults:
    async def test_import_defaults_idempotent(self, auth_client, account, db):
        # Account already has categories from conftest; import should be idempotent
        resp = await auth_client.post("/api/v1/me/categories/import-defaults")
        assert resp.status_code == 200
        data = resp.json()
        names = {c["name"] for c in data}
        # Should have all defaults
        assert "groceries" in names
        assert "electronics" in names
        assert "other" in names
        assert "transport" in names

    async def test_import_defaults_adds_missing(self, auth_client, account, db):
        # Delete a category, then import should re-create it
        cat = await db.execute(
            select(Category).where(
                Category.account_id == account.id, Category.name == "clothing"
            )
        )
        cat_obj = cat.scalar_one()
        await db.delete(cat_obj)
        await db.commit()

        resp = await auth_client.post("/api/v1/me/categories/import-defaults")
        assert resp.status_code == 200
        names = {c["name"] for c in resp.json()}
        assert "clothing" in names


class TestResolveOrphan:
    async def test_resolve_orphan(self, auth_client, account, db):
        cat = await db.execute(
            select(Category).where(
                Category.account_id == account.id, Category.name == "electronics"
            )
        )
        cat_obj = cat.scalar_one()
        resp = await auth_client.post(
            "/api/v1/me/categories/resolve-orphan",
            json={
                "raw_category": "quantum_parts",
                "category_id": cat_obj.id,
                "create_alias": True,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["resolved"] is True
        assert data["category"] == "electronics"

        # Verify alias was created
        alias = await db.execute(
            select(CategoryAlias).where(
                CategoryAlias.account_id == account.id,
                CategoryAlias.alias == "quantum_parts",
            )
        )
        assert alias.scalar_one_or_none() is not None

    async def test_resolve_orphan_nonexistent_category(self, auth_client, account):
        resp = await auth_client.post(
            "/api/v1/me/categories/resolve-orphan",
            json={
                "raw_category": "test",
                "category_id": "nonexistent-id",
                "create_alias": True,
            },
        )
        assert resp.status_code == 404
