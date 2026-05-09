from __future__ import annotations

from typing import Optional

from app.database.connection import get_pool
from app.services.cache_invalidation import (
    invalidate_category_catalog,
    invalidate_waifu_catalog,
)


_catalog_revision: Optional[int] = None


async def ensure_catalog_state_ready() -> None:
    pool = get_pool()
    if pool is None:
        raise RuntimeError("Database pool is not initialized")

    async with pool.acquire() as conn:
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS catalog_state (
                id SMALLINT PRIMARY KEY DEFAULT 1 CHECK (id = 1),
                revision BIGINT NOT NULL DEFAULT 1,
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """
        )
        await conn.execute(
            """
            ALTER TABLE catalog_state
            ADD COLUMN IF NOT EXISTS revision BIGINT
            """
        )
        await conn.execute(
            """
            ALTER TABLE catalog_state
            ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ
            """
        )
        await conn.execute(
            """
            INSERT INTO catalog_state (id, revision)
            VALUES (1, 1)
            ON CONFLICT (id) DO NOTHING
            """
        )
        await conn.execute(
            """
            UPDATE catalog_state
            SET revision = COALESCE(revision, 1),
                updated_at = COALESCE(updated_at, NOW())
            WHERE id = 1
            """
        )
        await conn.execute(
            """
            ALTER TABLE catalog_state
            ALTER COLUMN revision SET DEFAULT 1
            """
        )
        await conn.execute(
            """
            ALTER TABLE catalog_state
            ALTER COLUMN revision SET NOT NULL
            """
        )
        await conn.execute(
            """
            ALTER TABLE catalog_state
            ALTER COLUMN updated_at SET DEFAULT NOW()
            """
        )
        await conn.execute(
            """
            ALTER TABLE catalog_state
            ALTER COLUMN updated_at SET NOT NULL
            """
        )


async def _fetch_catalog_revision() -> int:
    pool = get_pool()
    if pool is None:
        raise RuntimeError("Database pool is not initialized")

    await ensure_catalog_state_ready()

    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT revision
            FROM catalog_state
            WHERE id = 1
            """
        )

    if row is None:
        return 1
    return int(row["revision"])


async def ensure_catalog_revision_current() -> None:
    global _catalog_revision

    latest_revision = await _fetch_catalog_revision()
    if _catalog_revision != latest_revision:
        invalidate_waifu_catalog()
        invalidate_category_catalog()
        _catalog_revision = latest_revision


async def bump_catalog_revision() -> int:
    global _catalog_revision

    pool = get_pool()
    if pool is None:
        raise RuntimeError("Database pool is not initialized")

    await ensure_catalog_state_ready()

    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            UPDATE catalog_state
            SET revision = revision + 1,
                updated_at = NOW()
            WHERE id = 1
            RETURNING revision
            """
        )

    if row is None:
        latest = await _fetch_catalog_revision()
    else:
        latest = int(row["revision"])

    _catalog_revision = latest
    return latest
