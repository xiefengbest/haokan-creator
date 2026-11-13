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

执行这一行，然后重新打开终端：

```bash
git clone https://github.com/xiefengbest/haokan-creator.git ~/.haokan-creator/repo && bash ~/.haokan-creator/repo/install.sh
```

装好后先读本目录旁边的技能说明，再帮用户添加创作者账号。没登录成功之前，不要发布。用户没明确说发布之前，不要上传。

## 账号

```bash
creator profile list
printf '%s' '密码' | creator profile add --name 创作者名 --phone +8613800138000 --password-stdin
creator profile use 创作者名
creator --profile 创作者名 auth status
```

密码只用 `--password-stdin`。不要把密码写进命令参数、技能说明或仓库。有多个号又没说用哪一个时，先列出名称让用户选。

这个 GitHub 仓库是公开的。后台地址、OSS 和签名只写在安装目录的 `.env`。文件缺失或是空的时停下来，让用户联系维护者填写。不要从网页或仓库历史里把这些值找回来写进代码，不要写进回复，也不要提交 `.env`。

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

合辑新建、修改、删除，作品修改、删除，创作者资料修改，都还没有命令。直接告诉用户还没开放。不要自己拼创作者接口，不要用浏览器登录后去改。
