"""Time helpers — unified Asia/Shanghai (UTC+8) timezone."""
from datetime import datetime
from typing import Optional
from zoneinfo import ZoneInfo

SHANGHAI_TZ = ZoneInfo("Asia/Shanghai")


def shanghai_now() -> datetime:
    """Current time in Asia/Shanghai (naive, for DB DateTime columns)."""
    return datetime.now(SHANGHAI_TZ).replace(tzinfo=None)


def ensure_shanghai(dt: Optional[datetime]) -> Optional[datetime]:
    """Attach or convert to Asia/Shanghai."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=SHANGHAI_TZ)
    return dt.astimezone(SHANGHAI_TZ)


def to_shanghai_iso(dt: Optional[datetime]) -> Optional[str]:
    """Serialize datetime for JSON/API (Asia/Shanghai with +08:00)."""
    dt = ensure_shanghai(dt)
    if dt is None:
        return None
    return dt.isoformat()


# Backward-compatible alias
utc_now = shanghai_now
