from app.admin.services.admin_auth_service import is_admin_authorized, logout_admin


async def is_admin_session_active(user_id: int) -> bool:
    return await is_admin_authorized(user_id)


async def revoke_admin_session(user_id: int) -> None:
    await logout_admin(user_id)
