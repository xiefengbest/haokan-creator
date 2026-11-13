# Changelog

格式基于实际交付日期。**版本号只维护在 `pyproject.toml`。**

## 0.1.4 — 2026-11-13

- 修复 pip 安装到 venv 后导入即崩溃（版本号改读包元数据）。
- 发布支持 `--content`；尺寸列表增加 `isCover`；已删/不存在作品返回明确错误。

## 0.1.3 — 2026-11-13

- `creator update` 与安装拉源码：优先 GitHub，失败回退国内 CDN。

## 0.1.2 — 2026-11-13

- 文档与安装页：国内 CDN 链接、更新说明（Git 自动更新 vs CDN 用 `creator update` / 重装脚本）。
- `creator update` 支持 CDN 安装副本；Python 3.9+ 检查；打包排除 `._*` / `.DS_Store`；`haokan-creator.tar.gz` 与当前版本包同步。

## 0.1.1 — 2026-11-13

- 按天排期发布同时提交当天 `endTime`（23:59:59）。
- 国内 CDN：带 commit 的安装包 + `manifest.json`；安装脚本按清单下载，减少缓存旧包。
- 安装指南与 skill：白话添加账号、国内安装、能力范围与已开放命令说明。

## 0.1.0 — 2026-11-13

- 首批公开 CLI：安装、账号、合辑/作品/资料、国内 CDN 安装入口。
