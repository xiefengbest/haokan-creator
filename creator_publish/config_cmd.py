"""检查与导入本机后台配置。"""

from __future__ import annotations

import os
import shutil
from pathlib import Path

from creator_publish.config import ENV_PATH, data_home, load_env_file

COMMON_KEYS = (
    "CREATOR_SIGN_KEY",
    "CREATOR_COMPANY_ID",
    "CREATOR_CLIENT_TYPE",
    "CREATOR_API_VERSION",
    "CREATOR_STS_URL",
)
REGION_KEYS = {
    "cn": (
        "CREATOR_CN_API",
        "CREATOR_CN_OSS_RES",
        "CREATOR_CN_BUCKET",
        "CREATOR_CN_ENDPOINT",
    ),
    "xjp": (
        "CREATOR_XJP_API",
        "CREATOR_XJP_OSS_RES",
        "CREATOR_XJP_BUCKET",
        "CREATOR_XJP_ENDPOINT",
    ),
}


def backend_env_path() -> Path:
    return data_home() / "backend.env"


def _parse_env_map(path: Path) -> dict[str, str]:
    if not path.is_file():
        return {}
    values: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        cleaned = value.strip().strip('"').strip("'")
        if cleaned:
            values[key.strip()] = cleaned
    return values


def merged_backend_values() -> dict[str, str]:
    merged: dict[str, str] = {}
    merged.update(_parse_env_map(backend_env_path()))
    merged.update(_parse_env_map(ENV_PATH))
    return merged


def required_keys(region: str) -> tuple[str, ...]:
    normalized = region.lower()
    if normalized in {"sg", "singapore", "global"}:
        normalized = "xjp"
    if normalized not in REGION_KEYS:
        normalized = "cn"
    return COMMON_KEYS + REGION_KEYS[normalized]


def inspect_backend() -> dict:
    backend = backend_env_path()
    optional = ENV_PATH
    values = _parse_env_map(backend)
    region = values.get("CREATOR_REGION", "cn").lower()
    if not values and optional.is_file():
        region = _parse_env_map(optional).get("CREATOR_REGION", "cn").lower()
    missing = [key for key in required_keys(region) if not values.get(key)]
    return {
        "backendEnv": str(backend),
        "backendEnvExists": backend.is_file(),
        "optionalEnvExists": optional.is_file(),
        "region": region,
        "ready": backend.is_file() and not missing,
        "missingKeys": missing,
    }


def import_backend(source: Path) -> Path:
    if not source.is_file():
        raise SystemExit(f"找不到文件：{source}")
    values = _parse_env_map(source)
    if not values:
        raise SystemExit("这个文件里没有可用的配置项。")
    region = values.get("CREATOR_REGION", "cn")
    missing = [key for key in required_keys(region) if not values.get(key)]
    if missing:
        raise SystemExit(f"这份配置还缺：{'、'.join(missing)}。请向谢峰索取完整 backend.env。")
    target = backend_env_path()
    target.parent.mkdir(parents=True, mode=0o700, exist_ok=True)
    os.chmod(target.parent, 0o700)
    shutil.copyfile(source, target)
    target.chmod(0o600)
    load_env_file(target)
    return target


def describe_status(payload: dict) -> str:
    if payload["ready"]:
        return "后台配置已就绪，可以登录和发布。"
    if not payload["backendEnvExists"]:
        return "还没有 backend.env。请执行 creator config import <谢峰提供的文件>。"
    return f"后台配置不完整，还缺：{'、'.join(payload['missingKeys'])}。"
