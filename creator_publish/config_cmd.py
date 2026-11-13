"""检查与导入本机后台配置。"""

from __future__ import annotations

import os
import shutil
from pathlib import Path

from creator_publish.config import ENV_PATH, apply_builtin_defaults, data_home, load_env_file

REQUIRED_KEYS = ("CREATOR_SIGN_KEY",)
OPTIONAL_KEYS = ("CREATOR_REGION",)


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


def inspect_backend() -> dict:
    backend = backend_env_path()
    optional = ENV_PATH
    values = _parse_env_map(backend)
    region = values.get("CREATOR_REGION", "cn").lower()
    if not values and optional.is_file():
        region = _parse_env_map(optional).get("CREATOR_REGION", "cn").lower()
    missing = [key for key in REQUIRED_KEYS if not values.get(key)]
    return {
        "backendEnv": str(backend),
        "backendEnvExists": backend.is_file(),
        "optionalEnvExists": optional.is_file(),
        "region": region,
        "ready": backend.is_file() and not missing,
        "missingKeys": missing,
        "usesBuiltinEndpoints": True,
    }


def import_backend(source: Path) -> Path:
    if not source.is_file():
        raise SystemExit(f"找不到文件：{source}")
    values = _parse_env_map(source)
    if not values:
        raise SystemExit("这个文件里没有可用的配置项。")
    missing = [key for key in REQUIRED_KEYS if not values.get(key)]
    if missing:
        raise SystemExit(f"这份配置还缺：{'、'.join(missing)}。向谢峰索取 CREATOR_SIGN_KEY 即可，其它地址 CLI 已内置。")
    target = backend_env_path()
    target.parent.mkdir(parents=True, mode=0o700, exist_ok=True)
    os.chmod(target.parent, 0o700)
    lines = []
    keep = set(REQUIRED_KEYS + OPTIONAL_KEYS)
    for raw in source.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key = line.split("=", 1)[0].strip()
        if key in keep:
            lines.append(f"{key}={values[key]}")
    if "CREATOR_REGION" not in values:
        lines.append("CREATOR_REGION=cn")
    target.write_text("\n".join(lines) + "\n", encoding="utf-8")
    target.chmod(0o600)
    load_env_file(target)
    apply_builtin_defaults(values.get("CREATOR_REGION", "cn"))
    return target


def describe_status(payload: dict) -> str:
    if payload["ready"]:
        return "后台配置已就绪（签名密钥已配置，接口地址使用内置默认值），可以登录和发布。"
    if not payload["backendEnvExists"]:
        return "还没有 backend.env。请执行 creator config import <谢峰提供的文件>，文件里只需 CREATOR_SIGN_KEY。"
    return f"后台配置不完整，还缺：{'、'.join(payload['missingKeys'])}。"
