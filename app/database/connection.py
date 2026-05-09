import asyncpg
from app.config import config

pool = None


async def create_pool():
    global pool

    pool = await asyncpg.create_pool(
        host=config.DB_HOST,
        port=config.DB_PORT,
        user=config.DB_USER,
        password=config.DB_PASSWORD,
        database=config.DB_NAME
    )

    from app.services.catalog_state_service import ensure_catalog_state_ready
    from app.database.schema import ensure_runtime_schema

    await ensure_catalog_state_ready()
    await ensure_runtime_schema()


def get_pool():
    return pool