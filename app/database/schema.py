from __future__ import annotations

from app.database.connection import get_pool


async def ensure_runtime_schema() -> None:
    pool = get_pool()
    if pool is None:
        raise RuntimeError("Database pool is not initialized")

    async with pool.acquire() as conn:
        # Core catalog tables
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS categories (
                id SERIAL PRIMARY KEY,
                name_ru TEXT NOT NULL,
                name_en TEXT NOT NULL,
                parent_id INTEGER,
                node_type TEXT NOT NULL DEFAULT 'branch',
                is_active BOOLEAN NOT NULL DEFAULT TRUE,
                sort_order INTEGER NOT NULL DEFAULT 0,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                FOREIGN KEY (parent_id) REFERENCES categories(id) ON DELETE CASCADE
            )
            """
        )
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS waifus (
                id SERIAL PRIMARY KEY,
                name_ru TEXT NOT NULL,
                name_en TEXT NOT NULL,
                alias TEXT,
                alias_ru TEXT,
                alias_en TEXT,
                age TEXT,
                gender TEXT,
                rarity TEXT NOT NULL,
                category_id INTEGER NOT NULL,
                is_active BOOLEAN NOT NULL DEFAULT TRUE,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE CASCADE
            )
            """
        )
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS waifu_media (
                id SERIAL PRIMARY KEY,
                waifu_id INTEGER NOT NULL,
                media_type TEXT NOT NULL,
                file_id TEXT NOT NULL,
                is_primary BOOLEAN NOT NULL DEFAULT TRUE,
                sort_order INTEGER NOT NULL DEFAULT 1,
                FOREIGN KEY (waifu_id) REFERENCES waifus(id) ON DELETE CASCADE
            )
            """
        )
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                user_id BIGINT UNIQUE NOT NULL,
                username TEXT,
                language TEXT DEFAULT 'ru',
                favorite_waifu_id INTEGER,
                favorite_category_id INTEGER,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """
        )
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS user_claims (
                id BIGSERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL,
                waifu_id INTEGER NOT NULL,
                chat_id BIGINT,
                claimed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
                FOREIGN KEY (waifu_id) REFERENCES waifus(id) ON DELETE CASCADE
            )
            """
        )
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS chat_settings (
                chat_id BIGINT PRIMARY KEY,
                language TEXT NOT NULL DEFAULT 'ru',
                pity_epic INTEGER NOT NULL DEFAULT 0,
                pity_legendary INTEGER NOT NULL DEFAULT 0,
                pity_unique INTEGER NOT NULL DEFAULT 0,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """
        )
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS chat_category_blocks (
                chat_id BIGINT NOT NULL,
                root_category_id INTEGER NOT NULL,
                PRIMARY KEY (chat_id, root_category_id),
                FOREIGN KEY (root_category_id) REFERENCES categories(id) ON DELETE CASCADE
            )
            """
        )
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS user_waifus (
                user_id BIGINT NOT NULL,
                waifu_id INTEGER NOT NULL,
                amount INTEGER DEFAULT 1,
                PRIMARY KEY (user_id, waifu_id),
                FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
                FOREIGN KEY (waifu_id) REFERENCES waifus(id) ON DELETE CASCADE
            )
            """
        )

        # Catalog metadata for cache invalidation
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
            INSERT INTO catalog_state (id, revision)
            VALUES (1, 1)
            ON CONFLICT (id) DO NOTHING
            """
        )

        # Admin bootstrap / sessions / audit trail
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS admin_settings (
                id BIGSERIAL PRIMARY KEY,
                password_hash TEXT NOT NULL,
                auth_version BIGINT NOT NULL DEFAULT 1,
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_by BIGINT
            )
            """
        )
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS admin_users (
                user_id BIGINT PRIMARY KEY,
                role TEXT NOT NULL DEFAULT 'admin',
                failed_attempts INTEGER NOT NULL DEFAULT 0,
                locked_until TIMESTAMPTZ,
                permanent_ban BOOLEAN NOT NULL DEFAULT FALSE,
                auth_version_seen BIGINT NOT NULL DEFAULT 0,
                last_auth_at TIMESTAMPTZ
            )
            """
        )
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS admin_audit_log (
                id BIGSERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL,
                action TEXT NOT NULL,
                target_type TEXT,
                target_id BIGINT,
                payload JSONB,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """
        )

        # Optional compatibility table kept for older imports / legacy data
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS admins (
                user_id BIGINT PRIMARY KEY,
                username TEXT
            )
            """
        )

        # Backward-compatible column upgrades for older databases
        await conn.execute(
            """
            ALTER TABLE categories
            ADD COLUMN IF NOT EXISTS node_type TEXT NOT NULL DEFAULT 'branch',
            ADD COLUMN IF NOT EXISTS is_active BOOLEAN NOT NULL DEFAULT TRUE,
            ADD COLUMN IF NOT EXISTS sort_order INTEGER NOT NULL DEFAULT 0,
            ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            """
        )
        await conn.execute(
            """
            ALTER TABLE waifus
            ADD COLUMN IF NOT EXISTS gender TEXT,
            ADD COLUMN IF NOT EXISTS alias TEXT,
            ADD COLUMN IF NOT EXISTS alias_ru TEXT,
            ADD COLUMN IF NOT EXISTS alias_en TEXT,
            ADD COLUMN IF NOT EXISTS age TEXT,
            ADD COLUMN IF NOT EXISTS is_active BOOLEAN NOT NULL DEFAULT TRUE,
            ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            """
        )
        await conn.execute(
            """
            UPDATE waifus
            SET alias_ru = COALESCE(alias_ru, alias),
                alias_en = COALESCE(alias_en, alias)
            WHERE alias IS NOT NULL
              AND (alias_ru IS NULL OR alias_en IS NULL)
            """
        )
        await conn.execute(
            """
            ALTER TABLE waifu_media
            ADD COLUMN IF NOT EXISTS is_primary BOOLEAN NOT NULL DEFAULT TRUE,
            ADD COLUMN IF NOT EXISTS sort_order INTEGER NOT NULL DEFAULT 1
            """
        )
        await conn.execute(
            """
            ALTER TABLE users
            ADD COLUMN IF NOT EXISTS favorite_waifu_id INTEGER,
            ADD COLUMN IF NOT EXISTS favorite_category_id INTEGER,
            ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            """
        )
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS user_claims (
                id BIGSERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL,
                waifu_id INTEGER NOT NULL,
                chat_id BIGINT,
                claimed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
                FOREIGN KEY (waifu_id) REFERENCES waifus(id) ON DELETE CASCADE
            )
            """
        )
        await conn.execute(
            """
            ALTER TABLE chat_settings
            ADD COLUMN IF NOT EXISTS language TEXT NOT NULL DEFAULT 'ru',
            ADD COLUMN IF NOT EXISTS pity_epic INTEGER NOT NULL DEFAULT 0,
            ADD COLUMN IF NOT EXISTS pity_legendary INTEGER NOT NULL DEFAULT 0,
            ADD COLUMN IF NOT EXISTS pity_unique INTEGER NOT NULL DEFAULT 0,
            ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            """
        )
        await conn.execute(
            """
            ALTER TABLE catalog_state
            ADD COLUMN IF NOT EXISTS revision BIGINT,
            ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ
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

        # Useful indexes
        await conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_waifus_category
            ON waifus(category_id)
            """
        )
        await conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_categories_parent
            ON categories(parent_id)
            """
        )
        await conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_media_waifu
            ON waifu_media(waifu_id)
            """
        )
        await conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_user_waifus_user
            ON user_waifus(user_id)
            """
        )
        await conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_user_claims_user_claimed
            ON user_claims(user_id, claimed_at DESC)
            """
        )
        await conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_admin_audit_log_user_created
            ON admin_audit_log(user_id, created_at DESC)
            """
        )
