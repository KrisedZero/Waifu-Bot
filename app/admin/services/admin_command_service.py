from __future__ import annotations

from app.database.connection import get_pool


async def list_active_admin_sessions():
    pool = get_pool()
    if pool is None:
        return []

    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            WITH current_settings AS (
                SELECT auth_version
                FROM admin_settings
                ORDER BY id
                LIMIT 1
            )
            SELECT
                u.user_id,
                u.role,
                u.failed_attempts,
                u.locked_until,
                u.permanent_ban,
                u.auth_version_seen,
                u.last_auth_at,
                s.auth_version AS current_auth_version
            FROM admin_users u
            CROSS JOIN current_settings s
            WHERE u.auth_version_seen = s.auth_version
              AND u.permanent_ban = FALSE
              AND (u.locked_until IS NULL OR u.locked_until <= NOW())
            ORDER BY u.last_auth_at DESC NULLS LAST, u.user_id
            """
        )
        return rows
