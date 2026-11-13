"""本机创作者账号。密码只写在数据目录里，不进仓库。"""

from __future__ import annotations

import json
import os
from pathlib import Path

from creator_publish.config import APPLY_HINT, data_home


def profiles_path() -> Path:
    return data_home() / "profiles.json"


def load_store() -> dict:
    path = profiles_path()
    if not path.is_file():
        return {"active": "", "profiles": {}}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"账号文件损坏：{path}") from exc
    if not isinstance(data, dict):
        raise SystemExit(f"账号文件损坏：{path}")
    data.setdefault("active", "")
    data.setdefault("profiles", {})
    return data


def save_store(data: dict) -> None:
    path = profiles_path()
    path.parent.mkdir(parents=True, mode=0o700, exist_ok=True)
    os.chmod(path.parent, 0o700)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    os.chmod(path, 0o600)


def list_profiles() -> list[dict]:
    data = load_store()
    active = data.get("active") or ""
    rows = []
    for name, item in data.get("profiles", {}).items():
        rows.append(
            {
                "name": name,
                "active": name == active,
                "region": item.get("region") or "cn",
                "phone": mask_phone(item.get("phone") or ""),
            }
        )
    return rows


def add_profile(name: str, phone: str, password: str, region: str) -> None:
    from creator_publish.config import parse_phone

    cleaned = name.strip()
    if not cleaned:
        raise SystemExit("请填写账号名称，用创作者名字即可。")
    if not password:
        raise SystemExit("密码是空的。")
    if region not in {"cn", "xjp"}:
        raise SystemExit("区域只能是 cn 或 xjp。")
    try:
        parse_phone(phone)
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc
    data = load_store()
    profiles = data.setdefault("profiles", {})
    profiles[cleaned] = {"phone": phone.strip(), "password": password, "region": region}
    if not data.get("active"):
        data["active"] = cleaned
    save_store(data)


def use_profile(name: str) -> None:
    data = load_store()
    if name not in data.get("profiles", {}):
        raise SystemExit(f"没有这个账号：{name}")
    data["active"] = name
    save_store(data)


def remove_profile(name: str) -> None:
    data = load_store()
    profiles = data.get("profiles", {})
    if name not in profiles:
        raise SystemExit(f"没有这个账号：{name}")
    del profiles[name]
    if data.get("active") == name:
        data["active"] = next(iter(profiles), "")
    save_store(data)


def resolve_profile(name: str | None) -> dict:
    data = load_store()
    profiles = data.get("profiles", {})
    if not profiles:
        raise SystemExit(f"还没有创作者账号。{APPLY_HINT} 拿到之后执行 creator profile add。")
    chosen = (name or "").strip() or (data.get("active") or "")
    if not chosen:
        if len(profiles) == 1:
            chosen = next(iter(profiles))
        else:
            names = "、".join(profiles)
            raise SystemExit(f"这台电脑有多个创作者账号，请加上 --profile。现有：{names}")
    item = profiles.get(chosen)
    if not item:
        raise SystemExit(f"没有这个账号：{chosen}")
    return {"name": chosen, **item}


def apply_profile(name: str | None) -> dict:
    item = resolve_profile(name)
    os.environ["CREATOR_NAME"] = item["name"]
    os.environ["CREATOR_PHONE"] = item.get("phone") or ""
    os.environ["CREATOR_PASSWORD"] = item.get("password") or ""
    os.environ["CREATOR_REGION"] = item.get("region") or "cn"
    return item


def mask_phone(phone: str) -> str:
    digits = "".join(ch for ch in phone if ch.isdigit())
    if len(digits) < 7:
        return "***"
    return f"{digits[:3]}****{digits[-4:]}"
