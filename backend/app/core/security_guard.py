"""Wave 0 运行时安全护栏。不改表结构，不碰业务数据。"""
from __future__ import annotations

from urllib.parse import urlparse

from .config import Settings, settings

DEFAULT_JWT_SECRET = "videoforge-dev-secret-change-in-production"


class SecurityConfigError(RuntimeError):
    """生产配置不满足启动条件。"""


class ResetDenied(RuntimeError):
    """禁止在非开发本地环境重置数据库。"""


class UnsafeDatabaseOperation(RuntimeError):
    """无 WHERE 的 DELETE/UPDATE 被拒绝。"""


def normalize_app_env(value: str | None) -> str:
    v = (value or "").strip().lower()
    if v in {"dev", "development"}:
        return "development"
    if v == "test":
        return "test"
    if v == "production":
        return "production"
    return "development"


def allow_dev_echo(s: Settings | None = None) -> bool:
    s = s or settings
    env = normalize_app_env(s.app_env)
    return env in {"development", "test"} and bool(s.auth_dev_echo_code)


def cors_origin_list(s: Settings | None = None) -> list[str]:
    s = s or settings
    env = normalize_app_env(s.app_env)
    raw = [o.strip() for o in (s.cors_origins or "").split(",") if o.strip()]
    if env == "production":
        return raw
    if raw:
        return raw
    if env == "test":
        return ["http://testserver", "http://localhost:5173"]
    return ["http://localhost:5173", "http://127.0.0.1:5173", "http://[::1]:5173"]


def validate_runtime_settings(s: Settings | None = None) -> None:
    """生产环境启动前硬检查。失败即退出，不自动纠正、不打印 secret。"""
    s = s or settings
    env = normalize_app_env(s.app_env)
    if env != "production":
        return
    if not (s.jwt_secret or "").strip() or s.jwt_secret == DEFAULT_JWT_SECRET:
        raise SecurityConfigError("Production JWT_SECRET must be explicitly configured.")
    if s.debug:
        raise SecurityConfigError("Production DEBUG must be false.")
    if s.auth_dev_echo_code:
        raise SecurityConfigError("Production AUTH_DEV_ECHO_CODE must be false.")
    if not (s.database_url or "").strip():
        raise SecurityConfigError("Production DATABASE_URL must be explicitly configured.")
    origins = cors_origin_list(s)
    if not origins or "*" in origins:
        raise SecurityConfigError("Production CORS_ORIGINS must be an explicit origin list.")


def _url_host(database_url: str) -> str:
    parsed = urlparse(database_url)
    return (parsed.hostname or "").lower()


def assert_reset_allowed(s: Settings | None = None) -> None:
    """仅 APP_ENV=development 且数据库 host 为本地时允许 reset。test/production 一律拒绝。"""
    s = s or settings
    env = normalize_app_env(s.app_env)
    if env != "development":
        raise ResetDenied("database reset is only allowed when APP_ENV=development")
    url = (s.database_url or "").strip()
    if url and not url.startswith("sqlite"):
        host = _url_host(url)
        if host not in {"localhost", "127.0.0.1", ""}:
            raise ResetDenied("database reset is only allowed against localhost")
