# Haokan Creator

给编辑和代理用的创作者后台命令行。图片从本机直接传到对象存储，不经过别人的服务器。账号保存在 `~/.haokan-creator`。

[安装入口](docs/安装入口.md) · [安装指南](docs/安装指南.md) · [使用指南](docs/使用指南.md) · [技能说明](skills/) · [安全](#安全)

这个 GitHub 仓库是公开的。账号、密码和密钥需要联系谢峰申请。拿到之后只保存在这台电脑。

## 为什么用它

- 给代理用：四个技能说明告诉代理何时执行哪条命令，代理不需要再猜接口
- 命令直接执行：登录、预览、上传都在编辑自己的电脑上完成
- 先确认再改动：添加账号、切换账号、发布作品都会先停住，用户明确同意后才执行
- 公开仓库不放密钥：后台地址、签名和对象存储配置只写在本机 `.env`

## 现在能做的事

| 事项 | 能力 |
| --- | --- |
| 账号 | 在本机添加、查看、切换、删除创作者号，并检查能否登录 |
| 合辑 | 查看、新建、修改名称/简介/更新频率、删除 |
| 作品 | 预览并发布；修改描述/合辑/上线时间；删除 |
| 资料 | 查看和修改昵称、简介、头像链接、一条社交链接 |
| 更新 | 平时自动更新命令和技能说明。正在发布时不会中途更换程序 |

合辑封面和横滑封面、作品换图还不能用命令行上传，需要到创作者后台处理。

## 安装与快速开始

需要 Git、Python 3.9 或更新版本，以及 macOS 或 Linux。两种装法见 [安装入口](docs/安装入口.md)（也可打开 [docs/install.html](docs/install.html) 复制）。

**手动安装** — 复制到终端：

```bash
git clone https://github.com/xiefengbest/haokan-creator.git ~/.haokan-creator/repo && bash ~/.haokan-creator/repo/install.sh
```

**通过 AI Agent 安装** — 复制提示词给 Cursor、Claude Code、Codex、Trae 等：

```text
帮我安装 Haokan Creator：https://github.com/xiefengbest/haokan-creator/blob/main/docs/安装指南.md
```

代理请按链接阅读 [安装指南](docs/安装指南.md) 逐步执行。装好后重新打开终端，用 `creator auth status` 确认能登录。日常用法见 [使用指南](docs/使用指南.md)。

## 技能说明

安装脚本会把这些说明接到本机代理目录。发布、改合辑或改资料之前，先读 `creator-shared`。

| 技能 | 说明 |
| --- | --- |
| `creator-shared` | 安装、账号、确认后再执行、更新、公开仓库安全规则 |
| `creator-work` | 把本机图片预览并发布到已有合辑 |
| `creator-album` | 合辑尚未开放。遇到时停下来，不要自己请求接口 |
| `creator-profile` | 线上创作者资料尚未开放。本机账号的添加和切换已可用 |

## 命令

执行 `creator` 查看概览。某一次换号时，在命令前加上 `--profile 创作者名`，不会改掉默认号。

| 要做的事 | 命令 |
| --- | --- |
| 查看本机账号 | `creator profile list` |
| 查看合辑 | `creator album list` |
| 新建合辑 | `creator album +create --name 名 --desc 简介 --frequency daily` |
| 修改或删除合辑 | `creator album +update` / `creator album +delete` |
| 预览发布 | `creator work +publish --dir 文件夹 --album-id 合辑ID` |
| 修改或删除作品 | `creator work +update` / `creator work +delete` |
| 查看或修改资料 | `creator me +show` / `creator me +update` |
| 确认后执行 | 在命令末尾加上 `--yes` |
| 更新 | `creator update` |

这里只有这一层命令。没有通用接口调用。不要自己拼创作者后台的请求。

## 输出

`profile`、`auth`、`update` 成功时，结果在标准输出：

```json
{ "ok": true, "data": {} }
```

失败时，说明在标准错误，退出码不是 0：

```json
{ "ok": false, "error": { "message": "..." } }
```

退出码 `10` 不是失败，是在等用户确认。标准错误里有基本信息和变动：

```json
{ "ok": false, "error": { "type": "confirmation", "action": "...", "basic": {}, "change": "...", "hint": "..." } }
```

把 `basic` 和 `change` 告诉用户。用户明确同意后，把 `--yes` 加到原命令末尾再执行一次。不要自行加上。

发布预览的每张图写在标准输出。确认信息仍在标准错误。有不能发布的图片时，先让用户处理，不要上传。

## 安全

- 账号、密码和密钥需要联系谢峰申请。没有配置时引导用户申请，不要自己查找或编造
- 这些内容只放在本机 `.env` 和 `~/.haokan-creator`。不要写进仓库、技能说明或对话
- 报错不带出密钥和地址
- 添加、切换、删除和发布都必须先确认。`--dry-run` 只预览，不上传
- 改这个仓库的代理请先读 [AGENTS.md](AGENTS.md)
