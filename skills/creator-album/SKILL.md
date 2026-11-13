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

合辑的查看、新建、修改和删除还没有开放。告诉用户现在只能把作品发布到一个已经存在的合辑，合辑 ID 需要用户提供。还没有创作者账号或密钥时，请用户联系谢峰申请，不要继续。

不要自己请求创作者接口去建合辑、改合辑或删合辑。以后开放时，也要先给出基本信息和变动，用户确认后才执行。
