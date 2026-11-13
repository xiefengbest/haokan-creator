---
name: creator-work
description: >-
  把本机图片发布到创作者合辑，或修改、删除已有作品。Use when the user mentions 传图、发布作品、
  重传图片、一天一张、修改作品、删除作品、creator work +publish，或给出一个图片文件夹和合辑。
metadata:
  requires:
    bins: ["creator"]
---

# 发布作品

先读 [creator-shared](../creator-shared/SKILL.md)。没有 `creator` 命令时，按安装指南安装。

## 发布前确认

向用户确认四件事：图片文件夹、合辑 ID、用哪个创作者号、从哪一天开始。没说日期就立即发布。

## 发布

```bash
creator work +publish --dir <文件夹> --album-id <合辑ID> --content 作品描述 --start-date 2026-07-13
```

描述也可写在文件夹里的 `描述.txt`；`--content` 会覆盖 `描述.txt`。

这条命令只预览，不上传。用户明确同意后，在命令末尾加上 `--yes`。

## 修改作品

只能改描述、所属合辑和上线时间，不能换图片。

```bash
creator work +update --group-id <作品ID> --content 新描述
creator work +update --group-id <作品ID> --album-id <合辑ID>
creator work +update --group-id <作品ID> --immediate
creator work +update --group-id <作品ID> --start-date 2026-07-13
```

先不加 `--yes`。如果要换图片，请用户到创作者后台处理。

## 删除作品

```bash
creator work +delete --group-id <作品ID>
```

删除不能恢复。先告诉用户基本信息，用户同意后再加 `--yes`。
