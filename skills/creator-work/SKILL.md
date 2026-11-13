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

## 先给出变动

```bash
creator work +publish --dir <文件夹> --album-id <合辑ID> --start-date 2026-07-13
```

这条命令只预览，不上传。把标准输出里的每张图，以及标准错误里的创作者、合辑、文件夹、上线时间告诉用户。

## 用户明确同意之后

在同一条命令末尾加上 `--yes` 再执行。不要自行加上。同一文件夹、同一个合辑已经发过的会跳过。

文件夹可以是 `1.jpg` 配 `1横图.jpg`，或每个子文件夹里放 `竖图.jpg` 和 `横图.jpg`。方图可以不放。

## 不要做的事

不要删除作品，不要改已发布的图，不要自己请求创作者接口。这些还没有命令。
