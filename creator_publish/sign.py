"""业务接口签名。密钥和公司编号从本机配置读取，不写进仓库。"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from typing import Optional


def dumps(obj) -> str:
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"))


def canonical_body(body: dict) -> dict:
    return {key: body[key] for key in sorted(body)}


def make_sign(message_id: str, time_stamp: str, body: dict, secret: str) -> str:
    raw = f"{message_id}{time_stamp}{secret}{dumps(canonical_body(body))}"
    return hashlib.md5(raw.encode("utf-8")).hexdigest()


def build_header(
    body: dict,
    user_id: str = "",
    token: str = "",
    user_name: str = "",
    now: Optional[datetime] = None,
    message_id: Optional[str] = None,
    *,
    secret: str,
    company_id: int,
    client_type: int,
    api_version: str,
) -> dict:
    current = now or datetime.now()
    time_stamp = current.strftime("%Y%m%d%H%M%S")
    if message_id is None:
        import secrets
        message_id = f"{time_stamp}{secrets.randbelow(1000)}"
    return {
        "version": api_version,
        "messageID": message_id,
        "companyId": company_id,
        "clientType": client_type,
        "sign": make_sign(message_id, time_stamp, body, secret),
        "timeStamp": time_stamp,
        "uid": user_id,
        "userId": user_id,
        "token": token,
        "userName": user_name,
    }
