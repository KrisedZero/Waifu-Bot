from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from app.admin.config import admin_config
from app.database.connection import get_pool

PBKDF2_ITERATIONS = 260_000

FREE_ATTEMPTS = 5
TEMP_LOCK_START = 6
DAY_LOCK_START = 11
BAN_START = 16

TEMP_LOCK_DELTA = timedelta(minutes=30)
DAY_LOCK_DELTA = timedelta(days=1)


@dataclass(slots=True)
class AdminAuthResult:
    ok: bool
    reason: str
    wait_seconds: int = 0
    attempts_left: int = 0


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _hash_password(password: str, salt: bytes | None = None) -> str:
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        PBKDF2_ITERATIONS,
    )
    return "pbkdf2_sha256${}${}${}".format(
        PBKDF2_ITERATIONS,
        base64.b64encode(salt).decode("utf-8"),
        base64.b64encode(digest).decode("utf-8"),
    )


def _verify_password(password: str, encoded: str) -> bool:
    try:
        algo, iter_s, salt_b64, digest_b64 = encoded.split("$", 3)
        if algo != "pbkdf2_sha256":
            return False

        iterations = int(iter_s)
        salt = base64.b64decode(salt_b64.encode("utf-8"))
        expected = base64.b64decode(digest_b64.encode("utf-8"))

        digest = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt,
            iterations,
        )
        return hmac.compare_digest(digest, expected)
    except Exception:
        return False


async def _fetch_settings_row():
    pool = get_pool()
    if pool is None:
        return None
    async with pool.acquire() as conn:
        return await conn.fetchrow(
            """
            SELECT id, password_hash, auth_version, updated_at, updated_by
            FROM admin_settings
            ORDER BY id
            LIMIT 1
            """
        )


async def _fetch_admin_user_row(user_id: int):
    pool = get_pool()
    if pool is None:
        return None
    async with pool.acquire() as conn:
        return await conn.fetchrow(
            """
            SELECT user_id, role, failed_attempts, locked_until, permanent_ban,
                   auth_version_seen, last_auth_at
            FROM admin_users
            WHERE user_id = $1
            """,
            user_id,
        )


async def ensure_admin_bootstrap() -> None:
    row = await _fetch_settings_row()
    if row:
        return

    bootstrap_password = (admin_config.ADMIN_PASSWORD or "").strip()
    if not bootstrap_password:
        raise RuntimeError("ADMIN_PASSWORD is empty. Put bootstrap admin password into .env")

    pool = get_pool()
    if pool is None:
        raise RuntimeError("Database pool is not initialized")

    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO admin_settings (
                password_hash,
                auth_version,
                updated_at,
                updated_by
            )
            VALUES ($1, 1, NOW(), $2)
            """,
            _hash_password(bootstrap_password),
            admin_config.ADMIN_OWNER_ID or None,
        )


async def get_admin_auth_version() -> int:
    row = await _fetch_settings_row()
    if not row:
        return 0
    return int(row["auth_version"] or 0)


async def is_admin_authorized(user_id: int) -> bool:
    settings = await _fetch_settings_row()
    if not settings:
        return False

    user = await _fetch_admin_user_row(user_id)
    if not user:
        return False

    if user["permanent_ban"]:
        return False

    locked_until = user["locked_until"]
    if locked_until and locked_until > _utcnow():
        return False

    return int(user["auth_version_seen"] or 0) == int(settings["auth_version"] or 0)


async def _set_admin_session(user_id: int) -> None:
    settings = await _fetch_settings_row()
    if not settings:
        raise RuntimeError("admin_settings is not initialized")

    pool = get_pool()
    if pool is None:
        raise RuntimeError("Database pool is not initialized")

    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO admin_users (
                user_id,
                role,
                failed_attempts,
                locked_until,
                permanent_ban,
                auth_version_seen,
                last_auth_at
            )
            VALUES ($1, 'admin', 0, NULL, FALSE, $2, NOW())
            ON CONFLICT (user_id)
            DO UPDATE SET
                role = EXCLUDED.role,
                failed_attempts = 0,
                locked_until = NULL,
                permanent_ban = FALSE,
                auth_version_seen = EXCLUDED.auth_version_seen,
                last_auth_at = NOW()
            """,
            user_id,
            int(settings["auth_version"]),
        )


def _attempt_policy(failed_attempts: int) -> tuple[bool, timedelta | None, str]:
    if failed_attempts >= BAN_START:
        return True, None, "permanent_ban"
    if failed_attempts >= DAY_LOCK_START:
        return False, DAY_LOCK_DELTA, "locked"
    if failed_attempts >= TEMP_LOCK_START:
        return False, TEMP_LOCK_DELTA, "locked"
    return False, None, "wrong_password"


async def _mark_failed_attempt(user_id: int) -> AdminAuthResult:
    settings = await _fetch_settings_row()
    if not settings:
        return AdminAuthResult(ok=False, reason="bootstrap_missing")

    now = _utcnow()
    user = await _fetch_admin_user_row(user_id)
    failed_attempts = int(user["failed_attempts"]) + 1 if user else 1

    permanent_ban, lock_delta, reason = _attempt_policy(failed_attempts)
    locked_until = now + lock_delta if lock_delta else None

    pool = get_pool()
    if pool is None:
        raise RuntimeError("Database pool is not initialized")

    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO admin_users (
                user_id,
                role,
                failed_attempts,
                locked_until,
                permanent_ban,
                auth_version_seen,
                last_auth_at
            )
            VALUES ($1, 'admin', $2, $3, $4, 0, NOW())
            ON CONFLICT (user_id)
            DO UPDATE SET
                failed_attempts = EXCLUDED.failed_attempts,
                locked_until = EXCLUDED.locked_until,
                permanent_ban = EXCLUDED.permanent_ban,
                last_auth_at = NOW()
            """,
            user_id,
            failed_attempts,
            locked_until,
            permanent_ban,
        )

    wait_seconds = max(0, int((locked_until - now).total_seconds())) if locked_until else 0
    if failed_attempts <= FREE_ATTEMPTS:
        attempts_left = FREE_ATTEMPTS - failed_attempts
    elif failed_attempts < BAN_START:
        attempts_left = BAN_START - failed_attempts
    else:
        attempts_left = 0

    return AdminAuthResult(
        ok=False,
        reason=reason,
        wait_seconds=wait_seconds,
        attempts_left=attempts_left,
    )


async def authenticate_admin_password(user_id: int, password: str) -> AdminAuthResult:
    await ensure_admin_bootstrap()

    settings = await _fetch_settings_row()
    if not settings:
        return AdminAuthResult(ok=False, reason="bootstrap_missing")

    user = await _fetch_admin_user_row(user_id)
    now = _utcnow()

    if user and user["permanent_ban"]:
        return AdminAuthResult(ok=False, reason="permanent_ban")

    locked_until = user["locked_until"] if user else None
    if locked_until and locked_until > now:
        if _verify_password(password, settings["password_hash"]):
            return AdminAuthResult(
                ok=False,
                reason="locked",
                wait_seconds=max(0, int((locked_until - now).total_seconds())),
            )
        return await _mark_failed_attempt(user_id)

    if _verify_password(password, settings["password_hash"]):
        await _set_admin_session(user_id)
        return AdminAuthResult(ok=True, reason="ok")

    return await _mark_failed_attempt(user_id)


async def change_admin_password(new_password: str, updated_by: int) -> None:
    await ensure_admin_bootstrap()
    if updated_by != admin_config.ADMIN_OWNER_ID:
        raise PermissionError("Only owner can change admin password")

    new_hash = _hash_password(new_password)
    pool = get_pool()
    if pool is None:
        raise RuntimeError("Database pool is not initialized")

    async with pool.acquire() as conn:
        await conn.execute(
            """
            UPDATE admin_settings
            SET password_hash = $1,
                auth_version = auth_version + 1,
                updated_at = NOW(),
                updated_by = $2
            WHERE id = (
                SELECT id
                FROM admin_settings
                ORDER BY id
                LIMIT 1
            )
            """,
            new_hash,
            updated_by,
        )


async def logout_admin(user_id: int) -> None:
    pool = get_pool()
    if pool is None:
        return
    async with pool.acquire() as conn:
        await conn.execute(
            """
            UPDATE admin_users
            SET auth_version_seen = 0,
                last_auth_at = NULL
            WHERE user_id = $1
            """,
            user_id,
        )
