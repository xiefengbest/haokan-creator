"""上传原图，并让 OSS 按裁切参数另存成品。"""

from __future__ import annotations

import base64
import json
import time

from creator_publish.config import Settings


def encode_object_name(value: str) -> str:
    return base64.urlsafe_b64encode(value.encode("utf-8")).decode("ascii")


def parse_image_info(payload: dict) -> tuple[int, int]:
    return _info_value(payload, "ImageWidth", "imageWidth"), _info_value(payload, "ImageHeight", "imageHeight")


def _info_value(payload: dict, *names: str) -> int:
    for name in names:
        if name not in payload:
            continue
        value = payload[name]
        if isinstance(value, dict):
            value = value.get("value")
        return int(value)
    raise RuntimeError("OSS 没有返回图片宽高")


class OssStore:
    def __init__(self, bucket, bucket_name: str):
        self.bucket = bucket
        self.bucket_name = bucket_name

    def put_bytes(self, key: str, data: bytes, content_type: str) -> None:
        result = self.bucket.put_object(key, data, headers={"Content-Type": content_type})
        status = getattr(result, "status", 200)
        if status >= 300:
            raise RuntimeError(f"上传 {key} 失败，HTTP {status}")

    def crop_save(self, source_key: str, process: str, target_key: str) -> tuple[int, int]:
        style = f"{process}|sys/saveas,o_{encode_object_name(target_key)},b_{encode_object_name(self.bucket_name)}"
        result = self.bucket.process_object(source_key, style)
        status = getattr(result, "status", 200)
        if status >= 300:
            raise RuntimeError(f"裁切 {target_key} 失败，HTTP {status}")
        last_error = None
        for attempt in range(3):
            try:
                return self.image_size(target_key)
            except Exception as exc:
                last_error = exc
                time.sleep(0.4 * (attempt + 1))
        raise RuntimeError(f"裁切结果暂时读不到：{target_key}") from last_error

    def image_size(self, key: str) -> tuple[int, int]:
        result = self.bucket.get_object(key, process="image/info")
        payload = json.loads(result.read())
        return parse_image_info(payload)


def make_bucket(creds: dict, settings: Settings):
    import oss2

    auth = oss2.StsAuth(creds["access_key_id"], creds["access_key_secret"], creds["security_token"])
    return oss2.Bucket(auth, settings.endpoint, settings.bucket)
