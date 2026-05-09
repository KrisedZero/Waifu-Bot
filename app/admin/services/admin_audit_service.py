from __future__ import annotations

import json
from typing import Any

import asyncpg


async def write_audit_log(
    pool: asyncpg.Pool,
    *,
    user_id: int,
    action: str,
    target_type: str | None = None,
    target_id: int | None = None,
    payload: dict[str, Any] | None = None,
) -> None:
    await pool.execute(
        """
        INSERT INTO admin_audit_log (user_id, action, target_type, target_id, payload)
        VALUES ($1, $2, $3, $4, $5::jsonb)
        """,
        user_id,
        action,
        target_type,
        target_id,
        json.dumps(payload or {}, ensure_ascii=False),
    )
