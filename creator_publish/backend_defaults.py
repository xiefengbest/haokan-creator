"""生产环境默认后台参数。编辑只需配置 CREATOR_SIGN_KEY；维护者仍可用环境变量覆盖。"""

from __future__ import annotations

from typing import TypedDict


class RegionEndpoints(TypedDict):
    api: str
    oss_res: str
    bucket: str
    endpoint: str


COMMON = {
    "company_id": 10126,
    "client_type": 29,
    "api_version": '5851',
    "sts_url": 'https://token.levect.com/social/authFileTokenForCreator',
}

REGIONS: dict[str, RegionEndpoints] = {
    "cn": {
        "api": 'https://cnapi.levect.com',
        "oss_res": 'https://92cn-image.levect.com/',
        "bucket": 'hksocial',
        "endpoint": 'https://oss-cn-hangzhou.aliyuncs.com',
    },
    "xjp": {
        "api": 'https://social.levect.com',
        "oss_res": 'https://92image.levect.com/',
        "bucket": 'hk-92-social',
        "endpoint": 'https://oss-ap-southeast-1.aliyuncs.com',
    },
}


def apply_region_defaults(region: str, env: dict[str, str]) -> None:
    """用内置默认值补全 env（不覆盖已有项）。"""
    normalized = region.lower()
    if normalized in {"sg", "singapore", "global"}:
        normalized = "xjp"
    if normalized not in REGIONS:
        normalized = "cn"
    for key, value in COMMON.items():
        env_name = {
            "company_id": "CREATOR_COMPANY_ID",
            "client_type": "CREATOR_CLIENT_TYPE",
            "api_version": "CREATOR_API_VERSION",
            "sts_url": "CREATOR_STS_URL",
        }[key]
        if value and not env.get(env_name, "").strip():
            env[env_name] = str(value)
    region_vals = REGIONS[normalized]
    prefix = "CREATOR_CN" if normalized == "cn" else "CREATOR_XJP"
    mapping = {
        "api": f"{prefix}_API",
        "oss_res": f"{prefix}_OSS_RES",
        "bucket": f"{prefix}_BUCKET",
        "endpoint": f"{prefix}_ENDPOINT",
    }
    for field, env_name in mapping.items():
        val = region_vals[field]
        if val and not env.get(env_name, "").strip():
            env[env_name] = val
