---
name: creator-work
description: >-
  把本机图片发布到创作者合辑。Use when the user mentions 传图、发布作品、
  重传图片、一天一张、creator work +publish，或给出一个图片文件夹和合辑。
---

# 发布作品

先读 [creator-shared](../creator-shared/SKILL.md)。没有 `creator` 命令时，按那里的一行命令安装。

## 发布前确认

向用户确认四件事：图片文件夹、合辑 ID、用哪个创作者号、从哪一天开始。没说日期就立即发布。

## 先预览

```bash
creator work +publish --dir <文件夹> --album-id <合辑ID> --start-date 2026-07-13 --dry-run
```

换号时把 `--profile 创作者名` 放在最前面。预览不会登录，也不会上传。把通过几张、哪一张不能发、准备从哪天发到哪天告诉用户。

## 用户明确说发布之后

去掉 `--dry-run` 再执行同一条命令。不要擅自补上发布。同一文件夹、同一个合辑已经发过的会跳过。

文件夹可以是 `1.jpg` 配 `1横图.jpg`，或每个子文件夹里放 `竖图.jpg` 和 `横图.jpg`。方图可以不放。

## 不要做的事

不要删除作品，不要改已发布的图，不要自己请求创作者接口。这些还没有命令。
