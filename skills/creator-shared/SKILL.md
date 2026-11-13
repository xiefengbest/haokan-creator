---
name: creator-shared
description: >-
  安装和更新 Haokan Creator，管理本机创作者账号。Use when the user mentions
  Haokan Creator、创作者后台、creator profile、creator auth、creator update、
  安装创作者命令行，或要给创作者传图、改合辑、改作品之前。
---

# Haokan Creator 共用规则

命令行是 `creator`。账号、发布记录在 `~/.haokan-creator`，不要写进仓库，不要出现在回复里。

## 还没安装时

安装入口：https://github.com/xiefengbest/haokan-creator/blob/main/docs/安装入口.md

没装时，用户可以给助手这一句话：

```text
帮我安装 Haokan Creator：https://github.com/xiefengbest/haokan-creator/blob/main/docs/安装指南.md
```

按安装指南执行；克隆目录为 `~/.haokan-creator/repo`。装完后在对话里引导配置；用户问用法时读 `docs/使用指南.md`。

多数用户按安装指南第 1 步即可成功。仅当安装失败且日志含 `safe-delete`、`broker denied`、`egg-info` 时，再按少数机器的排障：请用户在**系统终端**执行安装命令，或安装 uv 后重跑 `install.sh`；对用户用白话说明，不要堆日志。

手动安装命令：

```bash
git clone https://github.com/xiefengbest/haokan-creator.git ~/.haokan-creator/repo && bash ~/.haokan-creator/repo/install.sh
```

没有创作者账号、密码或密钥时，请用户联系谢峰申请，不要自己查找或编造。后台配置用 `creator config import <文件>` 导入，用 `creator config status` 检查是否就绪。拿到之后再添加创作者账号。海外创作者用 `--region xjp` 或 `CREATOR_REGION=xjp`。没登录成功之前，不要发布。用户没明确说发布之前，不要上传。

## 账号

```bash
creator profile list
printf '%s' '密码' | creator profile add --name 创作者名 --phone +8613800138000 --password-stdin
creator profile use 创作者名
creator --profile 创作者名 auth status
```

密码只用 `--password-stdin`。不要把密码写进命令参数、技能说明、仓库或回复。有多个号又没说用哪一个时，先列出名称让用户选。

这个 GitHub 仓库是公开的。账号、密码和后台配置需要联系谢峰申请。后台配置通常只需 `CREATOR_SIGN_KEY`，放在 `~/.haokan-creator/backend.env`；接口与 OSS 地址 CLI 已内置，不要让编辑自己填十几项。命令提示还没有账号或后台配置时，停下来，请用户联系谢峰申请，不要继续。不要从网页或仓库历史里把这些值找回来。不要复述，也不要提交配置文件。

## 跟用户怎么说

用户是编辑或运营，不是工程师。**回复用户时只用自然语言**，不要在同一段里混写命令名、退出码、JSON 字段、环境变量名或本机路径。

- 后台配置成功：说「签名密钥已在这台电脑配好，可以登录创作者账号了」，不要说 `ready`、`CREATOR_SIGN_KEY`、`backend.env`。
- 要添加账号：说「请发创作者昵称和登录手机号；密码请私聊单独发」，不要描述 `--yes`、`--password-stdin`、退出码 `10` 的流程。
- 等待确认：用昵称、手机号尾号、将要做的动作说明，例如「准备在这台电脑上保存账号 XX，尾号 XXXX，确认后请你输入密码」。
- 密钥、密码、配置内容：不要在对话里复述。

技术细节只留在自己心里和安装指南里执行；用户看得懂的示例见 `docs/安装指南.md`「跟用户怎么说」表。

## 确认后再执行

新增、修改、删除都会先停住。退出码 `10` 不是失败，标准错误里有基本信息和将要发生的变动。把变动**翻成白话**告诉用户，等用户明确同意后，在原命令末尾加上 `--yes` 再执行一次。不要自行加上 `--yes`。

## 输出

`profile`、`auth`、`update` 成功时，标准输出是 `{"ok": true, ...}`。退出码 `10` 表示等待确认。其他失败看退出码，错误在标准错误。

## 更新

平时执行命令时，如果 GitHub 上有新版本，程序会先自动更新再继续。标准错误出现「已自动更新到最新版本」时，接着完成本次请求即可。

正在发布时不会中途更新。发布结束后如果看到「有新版本」，先把本次发布结果告诉用户，再执行：

```bash
creator update
```

## 还没有的能力

合辑封面和横滑封面、作品换图，还不能用命令行上传。需要时请用户到创作者后台处理。不要自己拼创作者接口。
