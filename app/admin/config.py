from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True, slots=True)
class AdminConfig:
    ADMIN_BOT_TOKEN: str
    ADMIN_OWNER_ID: int
    ADMIN_PASSWORD: str


def _load_int(name: str, default: str = "0") -> int:
    value = os.getenv(name, default).strip() if os.getenv(name, default) else default
    try:
        return int(value or "0")
    except ValueError:
        return 0


admin_config = AdminConfig(
    ADMIN_BOT_TOKEN=os.getenv("ADMIN_BOT_TOKEN", "").strip(),
    ADMIN_OWNER_ID=_load_int("ADMIN_OWNER_ID", "0"),
    ADMIN_PASSWORD=os.getenv("ADMIN_PASSWORD", "").strip(),
)
