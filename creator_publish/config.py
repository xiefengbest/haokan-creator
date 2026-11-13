"""读取 .env 与区域参数。"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path

APPLY_HINT = "账号、密码和密钥需要联系谢峰申请。拿到之后只保存在这台电脑，不要写进仓库或对话。"

TOOL_ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = TOOL_ROOT / ".env"
REPO_ROOT = TOOL_ROOT


def data_home() -> Path:
    override = os.environ.get("HAOKAN_CREATOR_HOME", "").strip()
    return Path(override).expanduser() if override else Path.home() / ".haokan-creator"


def output_dir() -> Path:
    path = data_home() / "output"
    path.mkdir(parents=True, exist_ok=True)
    return path

def load_env_file(path: Path = ENV_PATH) -> None:
    if not path.is_file():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


@dataclass(frozen=True)
class Settings:
    region: str
    api: str
    oss_res: str
    bucket: str
    endpoint: str
    phone: str
    password: str
    album_id: str
    creator_name: str
    album_name: str
    square_from: str
    phone_code: str
    sts_url: str = ""
    sign_key: str = ""
    company_id: int = 0
    client_type: int = 0
    api_version: str = ""

    def __repr__(self) -> str:
        return (
            f"Settings(region={self.region!r}, creator_name={self.creator_name!r}, "
            f"album_id={self.album_id!r})"
        )


def parse_phone(raw: str, phone_code: str = "+86") -> tuple[str, str]:
    text = re.sub(r"[\s-]", "", raw.strip())
    code = phone_code if phone_code.startswith("+") else f"+{phone_code}"
    if text.startswith("+"):
        if not text.startswith(code):
            raise ValueError(f"手机号区号需为 {code}，当前是 {text}")
        local = text[len(code) :]
    else:
        local = text
    if code == "+86" and not re.fullmatch(r"1\d{10}", local):
        raise ValueError("中国大陆手机号应为 11 位，例如 13800138000")
    if not local:
        raise ValueError("手机号为空")
    return code, local


def load_settings(require_account: bool) -> Settings:
    load_env_file()
    region = os.environ.get("CREATOR_REGION", "cn").strip().lower()
    if region in {"sg", "singapore", "global"}:
        region = "xjp"
    if region not in {"cn", "xjp"}:
        raise SystemExit("CREATOR_REGION 只能是 cn 或 xjp")
    square_from = os.environ.get("CREATOR_SQUARE_FROM", "portrait").strip().lower()
    if square_from not in {"portrait", "landscape"}:
        raise SystemExit("CREATOR_SQUARE_FROM 只能是 portrait 或 landscape")
    album_id = os.environ.get("CREATOR_ALBUM_ID", "").strip()
    prefix = "CREATOR_CN" if region == "cn" else "CREATOR_XJP"
    endpoint_name = {
        "api": f"{prefix}_API",
        "oss_res": f"{prefix}_OSS_RES",
        "bucket": f"{prefix}_BUCKET",
        "endpoint": f"{prefix}_ENDPOINT",
    }
    profile = {key: os.environ.get(name, "").strip() for key, name in endpoint_name.items()}
    sign_key = os.environ.get("CREATOR_SIGN_KEY", "").strip()
    sts_url = os.environ.get("CREATOR_STS_URL", "").strip()
    if require_account and (any(not profile[key] for key in endpoint_name) or not sign_key or not sts_url):
        raise SystemExit(f"本机还没有后台配置。{APPLY_HINT}")
    phone = os.environ.get("CREATOR_PHONE", "").strip()
    password = os.environ.get("CREATOR_PASSWORD", "")
    if require_account:
        if not phone or not password:
            raise SystemExit(f"还没有可用的创作者账号。{APPLY_HINT} 拿到之后执行 creator profile add，或在命令里加上 --profile。")
        if not album_id:
            raise SystemExit("请加上 --album-id，指定这次要发布的合辑。")
        try:
            parse_phone(phone, os.environ.get("CREATOR_PHONE_CODE", "+86"))
        except ValueError as exc:
            raise SystemExit(str(exc)) from exc
    return Settings(
        region=region,
        api=os.environ.get("CREATOR_API_URL", profile.get("api") or "").rstrip("/"),
        oss_res=profile.get("oss_res") or "",
        bucket=profile.get("bucket") or "",
        endpoint=profile.get("endpoint") or "",
        phone=phone,
        password=password,
        album_id=album_id,
        creator_name=os.environ.get("CREATOR_NAME", "").strip(),
        album_name=os.environ.get("CREATOR_ALBUM_NAME", "").strip(),
        square_from=square_from,
        phone_code=os.environ.get("CREATOR_PHONE_CODE", "+86"),
        sts_url=sts_url,
        sign_key=sign_key,
        company_id=int(os.environ.get("CREATOR_COMPANY_ID") or 0),
        client_type=int(os.environ.get("CREATOR_CLIENT_TYPE") or 0),
        api_version=os.environ.get("CREATOR_API_VERSION", "").strip(),
    )


def describe_account(settings: Settings) -> str:
    creator = settings.creator_name or "未填写创作者名称"
    album_id = settings.album_id or "未填写合辑 ID"
    if settings.album_name:
        return f"创作者 {creator}，合辑 {settings.album_name}（{album_id}）"
    return f"创作者 {creator}，合辑 {album_id}"
