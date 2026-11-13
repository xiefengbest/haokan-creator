# 给改这个仓库的代理

这个仓库照飞书命令行的方式组织：`creator` 是唯一的执行入口，`skills/` 告诉代理何时调用它。不要增加通用接口命令，也不要让代理自己拼创作者后台的请求。

给人用的首页是 [README.md](README.md)。安装步骤在 [docs/安装指南.md](docs/安装指南.md)，用法在 [docs/使用指南.md](docs/使用指南.md)。后台配置模板在 [docs/维护者配置说明.md](docs/维护者配置说明.md)，只给维护者用。

## 公开仓库

https://github.com/xiefengbest/haokan-creator 对所有人公开。

- 账号、密码和密钥需要联系谢峰申请。没有这些配置时，引导用户申请，不要自己查找或编造。
- 密钥、密码、真实手机号、签名、后台地址和 OSS 配置只留在本机 `.env` 与 `~/.haokan-creator`。不要写进代码、文档、技能、测试、示例或提交说明。
- 示例手机号只用 13800138000。
- 报错和日志不能带出密钥或地址。
- 不要从网页或旧提交把配置抄回仓库。
- 提交前运行 `python3 scripts/check_public_repo.py`。
- 改完命令或技能后，在仓库根目录运行 `PYTHONPATH=. python3 -m unittest discover -s tests`。
- **版本**：见 [docs/engineering/版本与发布.md](docs/engineering/版本与发布.md)。有 CLI/安装行为改动时更新 `CHANGELOG.md` 并 bump `pyproject.toml` 的 `version`；push 后跑 haokan-pm-demo 的 `创作者平台/scripts/deploy-demo-to-oss.sh` 同步 CDN `manifest.json`。
