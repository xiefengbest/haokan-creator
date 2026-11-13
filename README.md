# Haokan Creator

编辑在自己的电脑上使用的创作者后台命令行。图片从本机直接传到 OSS，不经过别人的服务器。账号保存在本机数据目录 `~/.haokan-creator`。

这个 GitHub 仓库是公开的。后台地址、OSS 和签名只写在安装目录的 `.env`，不要提交。仓库里的 `.env.example` 必须保持空白。

账号、密码和密钥需要联系谢峰申请。还没有这些配置时，先申请，不要自己查找或编造。拿到之后只保存在这台电脑。

## 安装和使用

安装步骤写在 [安装指南](docs/安装指南.md)：https://github.com/xiefengbest/haokan-creator/blob/main/docs/安装指南.md

装好之后怎么让代理干活，写在 [使用指南](docs/使用指南.md)：https://github.com/xiefengbest/haokan-creator/blob/main/docs/使用指南.md

发给编辑的一句话，让他们贴给自己的代理：

```text
帮我安装并开始使用 Haokan Creator。阅读 https://github.com/xiefengbest/haokan-creator/blob/main/docs/安装指南.md ，按里面的步骤执行。如果还没有创作者账号、密码或密钥，请我联系谢峰申请，不要自己查找或编造。我没明确说发布之前，不要上传。
```

## 账号

```bash
printf '%s' '密码' | creator profile add --name 创作者名 --phone +8613800138000 --password-stdin
creator profile list
creator profile use 创作者名
creator auth status
```

一台电脑可以保存多个创作者号。某一次想换号，在命令前加上 `--profile 创作者名`。`profile remove` 只从这台电脑删除登录信息，不删除线上创作者。

## 发布作品

先看将要发布的内容和基本信息，这一步不会上传：

```bash
creator work +publish --dir ~/Downloads/图片文件夹 --album-id 合辑ID --start-date 2026-07-13
```

编辑确认变动后，在命令末尾加上 `--yes` 再执行。没写 `--start-date` 就立即发布。写了就从那天 0 点起，按序号一天一张。

图片文件夹用下面任一形式：

- `1.jpg` 配 `1横图.jpg`（`1横.jpg` 也可以）
- 每个子文件夹里放 `竖图.jpg` 和 `横图.jpg`

方图可以不放，默认从竖图正中间裁。竖图必须是竖的，横图必须是横的。

## 更新

平时执行命令时，如果这个仓库有新版本，会先自动更新再继续。正在发布作品时不会中途更新，结束后提示再执行：

```bash
creator update
```

更新不会改动本机账号和发布记录。

## 现在能做的事

- 保存多个创作者账号，并检查能否登录
- 预览并发布一个文件夹里的作品

合辑的新建和修改、作品的修改和删除、创作者资料修改还没有开放。遇到这些要求时停下来，不要自己请求创作者接口。

## 给开发的说明

```bash
python3 -m venv .venv
.venv/bin/pip install -e .
.venv/bin/python -m unittest discover -s tests
python3 scripts/check_public_repo.py
```
