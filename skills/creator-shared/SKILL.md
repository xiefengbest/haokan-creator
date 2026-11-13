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
帮我安装 Haokan Creator：https://hk-h5-cdn.levect.com/html/xiefeng/creator/docs/安装指南.md
```

按安装指南执行；克隆目录为 `~/.haokan-creator/repo`。装完后在对话里引导配置；用户问用法时读 `docs/使用指南.md`。

多数用户按安装指南第 1 步即可成功。仅当安装失败且日志含 `safe-delete`、`broker denied`、`egg-info` 时，再按少数机器的排障：请用户在**系统终端**执行安装命令，或安装 uv 后重跑 `install.sh`；对用户用白话说明，不要堆日志。

手动安装命令：

```bash
curl -fsSL https://hk-h5-cdn.levect.com/html/xiefeng/creator/dist/install-from-cdn.sh | bash
```

可访问 GitHub 时也可：`git clone … && bash install.sh`（见安装指南）。

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

**禁止出现在用户可见回复里**（含 WorkBuddy 等）：`--yes`、`--password-stdin`、标准输入、管道、`printf`、退出码、`profile add`、命令行参数、日志、仓库、JSON。

- 后台配置成功：说「签名密钥已在这台电脑配好，可以登录创作者账号了」，不要说 `ready`、`CREATOR_SIGN_KEY`、`backend.env`。
- 要添加账号：先要昵称和手机号；跑完「预览/核对」命令后，用安装指南「添加账号·推荐话术」回复，说明**还没保存密码、暂不能发布**，请用户核对昵称和尾号，再在私聊发登录密码。
- 收到密码后：对用户只说「正在保存」→「已保存，登录正常」；技术执行在本地完成，不要复述密码或命令。
- 用户不愿在聊天里发密码：请用户在本机终端按安装指南自行完成，完成后由你代做 `auth status` 并用白话告知结果。
- 密钥、密码、配置内容：不要在对话里复述。

完整示例话术见 `docs/安装指南.md`「添加账号·推荐话术」。技术细节只留在自己心里执行。

## 确认后再执行

新增、修改、删除都会先停住。退出码 `10` 不是失败，标准错误里有基本信息和将要发生的变动。把变动**翻成白话**告诉用户，等用户明确同意后，在原命令末尾加上 `--yes` 再执行一次。不要自行加上 `--yes`。

## 输出

`profile`、`auth`、`update` 成功时，标准输出是 `{"ok": true, ...}`。退出码 `10` 表示等待确认。其他失败看退出码，错误在标准错误。

## 更新

- 更新统一用 `creator update`：**先 GitHub，不通再走 CDN**。对用户只说「我帮您检查一下有没有新版本」。
- 有 `.git` 时跑命令可能自动 `git pull`（见标准错误「已自动更新到最新版本」）。发布进行中不会中途更新。

## 能力范围

**可用命令**（先确认再加 `--yes`）：`creator album list` / `+create` / `+update` / `+delete`；`creator work +publish` / `+update` / `+delete`；`creator me +show` / `+update`。合辑与资料分别读 `creator-album`、`creator-profile`；发布读 `creator-work`。

**还没有**：合辑封面和横滑封面、作品换图，还不能用命令行上传。需要时请用户到创作者后台处理。不要自己拼创作者接口。
