"""登录、发布、登记尺寸。请求体按前台规则签名。"""

from __future__ import annotations

import warnings

warnings.filterwarnings("ignore", message="urllib3 v2 only supports OpenSSL")

import hashlib
import json
from dataclasses import dataclass
from typing import Optional

import requests

from creator_publish.config import Settings
from creator_publish.redact import redact
from creator_publish.sign import build_header, canonical_body, dumps


class ApiError(Exception):
    def __init__(self, action: str, payload):
        self.action = action
        self.payload = redact(payload)
        super().__init__(self.summary())

    def summary(self) -> str:
        header, body = unwrap(self.payload) if isinstance(self.payload, dict) else ({}, {})
        message = (
            body.get("err")
            or body.get("resMsg")
            or body.get("msg")
            or body.get("error")
            or header.get("resMsg")
            or header.get("resCode")
        )
        return f"{self.action}失败：{message or '接口没有返回成功'}"


@dataclass
class Session:
    user_id: str
    token: str
    user_name: str = ""


def unwrap(data: dict) -> tuple[dict, dict]:
    header = data.get("header") if isinstance(data.get("header"), dict) else {}
    body = data.get("body", data)
    if isinstance(body, str):
        try:
            body = json.loads(body)
        except json.JSONDecodeError:
            body = {"msg": body}
    if not isinstance(body, dict):
        body = {"msg": str(body)}
    return header, body


def ensure_ok(data: dict, action: str) -> dict:
    header, body = unwrap(data)
    res_code = header.get("resCode", header.get("rescode"))
    err = body.get("err") or body.get("resMsg")
    status = body.get("status")
    if res_code not in (None, "", 0, "0") or err not in (None, "", 0, "0") or status not in (None, 0, "0"):
        raise ApiError(action, data)
    return body


def find_text(obj, names: set[str]) -> Optional[str]:
    if isinstance(obj, dict):
        for key, value in obj.items():
            if key in names and value not in (None, ""):
                return str(value)
        for value in obj.values():
            found = find_text(value, names)
            if found:
                return found
    elif isinstance(obj, list):
        for item in obj:
            found = find_text(item, names)
            if found:
                return found
    return None


def pick(payload, names: set[str]) -> Optional[str]:
    if not isinstance(payload, dict):
        return None
    _, body = unwrap(payload)
    return find_text(body, names) or find_text(payload, names)


class CreatorClient:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.session: Optional[Session] = None
        self.http = requests.Session()

    def login(self) -> Session:
        from creator_publish.config import parse_phone

        code, local = parse_phone(self.settings.phone, self.settings.phone_code)
        checked = self.post(
            "/social/checkUser",
            {"userCode": f"{code}{local}", "flag": "1"},
            auth=False,
            action="检查账号",
            check=False,
        )
        _, checked_body = unwrap(checked)
        if str(checked_body.get("flag")) != "1":
            raise ApiError("检查账号", {"header": {}, "body": {"msg": "这个手机号还没注册创作者账号"}})
        logged = self.post(
            "/social/loginV2",
            {
                "loginType": 1,
                "flag": 1,
                "phoneCode": code,
                "wechatCode": local,
                "wechatId": local,
                "pass": hashlib.md5(self.settings.password.encode("utf-8")).hexdigest(),
            },
            auth=False,
            action="登录",
        )
        user_id = pick(logged, {"userId", "userID", "uid"})
        token = pick(logged, {"token", "accessToken"})
        user_name = pick(logged, {"userName", "nickName"}) or ""
        if not user_id or not token:
            raise ApiError(
                "登录",
                {"header": {}, "body": {"msg": "响应里没有 userId 或 token", "response": redact(logged)}},
            )
        self.session = Session(user_id, token, user_name)
        return self.session

    def oss_token(self) -> dict:
        if not self.session:
            raise ApiError("获取上传凭证", {"body": {"msg": "还没登录"}})
        body = self.post(self.settings.sts_url, {}, auth=True, action="获取上传凭证")
        access_key_id = pick(body, {"AccessKeyId", "accessKeyId"})
        access_key_secret = pick(body, {"AccessKeySecret", "accessKeySecret"})
        security_token = pick(body, {"SecurityToken", "securityToken"})
        if not access_key_id or not access_key_secret or not security_token:
            raise ApiError(
                "获取上传凭证",
                {"header": {}, "body": {"msg": "响应里没有临时密钥", "response": redact(body)}},
            )
        return {
            "access_key_id": access_key_id,
            "access_key_secret": access_key_secret,
            "security_token": security_token,
        }

    def release(self, body: dict) -> str:
        result = self.post("/creator/social/releaseimage", body, action="创建作品")
        group_id = pick(result, {"imageGroupId", "groupId"})
        if not group_id:
            raise ApiError(
                "创建作品",
                {"header": {}, "body": {"msg": "响应里没有作品 ID", "response": redact(result)}},
            )
        return group_id

    def add_sizes(self, group_id: str, entries: list[dict]) -> None:
        self.post(
            "/creator/social/imageaddsize",
            {"imageGroupId": str(group_id), "list": entries},
            action="登记尺寸",
        )

    def delete_work(self, group_id: str) -> None:
        self.post(
            "/social/deleteImg",
            {"groupId": int(group_id), "pStatus": 3},
            action="删除作品",
        )

    def post(self, url: str, body: dict, auth: bool = True, action: str = "请求", check: bool = True) -> dict:
        payload = dict(body)
        user_id = ""
        token = ""
        user_name = ""
        if auth:
            if not self.session:
                raise ApiError(action, {"body": {"msg": "还没登录"}})
            payload["userId"] = self.session.user_id
            payload["token"] = self.session.token
            user_id = self.session.user_id
            token = self.session.token
            user_name = self.session.user_name
        signed = canonical_body(payload)
        header = build_header(
            signed,
            user_id,
            token,
            user_name,
            secret=self.settings.sign_key,
            company_id=self.settings.company_id,
            client_type=self.settings.client_type,
            api_version=self.settings.api_version,
        )
        envelope = dumps({"header": header, "body": signed})
        target = url if url.startswith("http") else f"{self.settings.api}{url}"
        try:
            response = self.http.post(
                target,
                data=envelope.encode("utf-8"),
                headers={"Content-Type": "application/json; charset=utf-8"},
                timeout=(10, 60),
            )
        except requests.RequestException as exc:
            raise ApiError(action, {"body": {"msg": "网络请求失败"}}) from exc
        try:
            data = response.json()
        except ValueError as exc:
            raise ApiError(action, {"body": {"msg": "接口返回了无法识别的内容", "status": response.status_code}}) from exc
        if response.status_code >= 400:
            raise ApiError(action, data if isinstance(data, dict) else {"body": {"msg": "接口返回了无法识别的内容"}})
        if not isinstance(data, dict):
            raise ApiError(action, {"body": {"msg": "响应不是 JSON 对象"}})
        if check:
            ensure_ok(data, action)
        return data
