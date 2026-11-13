---
name: creator-album
description: >-
  创作者合辑的查看、新建、修改和删除。Use when the user mentions 合辑、专辑、
  新建合辑、修改合辑简介、更新频率、删除合辑。
metadata:
  requires:
    bins: ["creator"]
---

# 合辑

先读 [creator-shared](../creator-shared/SKILL.md)。

## 查看

```bash
creator album list
```

## 新建

更新频率必填：`daily`、`weekly`、`monthly`、`yearly`、`rotate`。

```bash
creator album +create --name 合辑名 --desc 简介 --frequency daily
```

先不加 `--yes`。把标准错误里的基本信息和变动告诉用户。用户同意后加 `--yes`。

## 修改

至少要改名称、简介或更新频率中的一项。

```bash
creator album +update --album-id <ID> --name 新名称 --desc 新简介 --frequency weekly
```

## 删除

```bash
creator album +delete --album-id <ID>
```

删除不能恢复。合辑里的作品需要用户另行处理。先确认，再加 `--yes`。

## 封面和横滑封面

命令行还不能上传合辑封面或横滑封面。需要改图片时，请用户到创作者后台处理。
