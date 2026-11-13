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

按安装指南逐步执行。安装前阅读 https://github.com/xiefengbest/haokan-creator/blob/main/docs/安装指南.md 。装好后阅读 `~/.haokan-creator/repo/docs/安装指南.md`。用户问能做什么、怎么发布时，阅读 `~/.haokan-creator/repo/docs/使用指南.md`。

```bash
git clone https://github.com/xiefengbest/haokan-creator.git ~/.haokan-creator/repo && bash ~/.haokan-creator/repo/install.sh
```

没有创作者账号、密码或密钥时，请用户联系谢峰申请，不要自己查找或编造。拿到之后再添加到本机。没登录成功之前，不要发布。用户没明确说发布之前，不要上传。

## 账号

```bash
creator profile list
printf '%s' '密码' | creator profile add --name 创作者名 --phone +8613800138000 --password-stdin
creator profile use 创作者名
creator --profile 创作者名 auth status
```

密码只用 `--password-stdin`。不要把密码写进命令参数、技能说明、仓库或回复。有多个号又没说用哪一个时，先列出名称让用户选。

这个 GitHub 仓库是公开的。账号、密码和密钥需要联系谢峰申请。命令提示还没有账号或后台配置时，停下来，请用户联系谢峰申请，不要继续。不要从网页或仓库历史里把这些值找回来。谢峰提供的内容只写入本机 `.env` 或本机账号，不要复述，也不要提交 `.env`。

## 确认后再执行

新增、修改、删除都会先停住。退出码 `10` 不是失败，标准错误里有基本信息和将要发生的变动。把这两部分告诉用户，等用户明确同意后，在原命令末尾加上 `--yes` 再执行一次。不要自行加上 `--yes`。

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
