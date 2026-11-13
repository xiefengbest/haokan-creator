---
name: creator-profile
description: >-
  查看或修改线上创作者资料，包括昵称、头像、简介和社交链接。Use when the user mentions
  创作者资料、头像、简介、社交链接、个人主页。不要和本机 creator profile 账号管理混淆。
metadata:
  requires:
    bins: ["creator"]
---

# 创作者资料

先读 [creator-shared](../creator-shared/SKILL.md)。本机账号的添加和切换仍用 `creator profile`，那只影响这台电脑用哪个号登录。

## 查看

```bash
creator me +show
```

## 修改

```bash
creator me +update --name 新昵称 --description 新简介 --avatar-url https://...
creator me +update --social-platform xiaohongshu --social-url https://...
creator me +update --clear-social
```

国内简介最多 200 个字，海外版最多 200 个单词。社交链接只能保留一个。

先不加 `--yes`。头像只接受已有的图片地址，命令行不会上传新头像文件。用户明确同意后再加 `--yes`。
