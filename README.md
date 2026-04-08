# Weixin Content Pipeline

这是一个面向微信公众号的内容生产工作区，用来把原始字幕、transcript、访谈记录或笔记整理成可发布的公众号文章，并支持配图生成与草稿箱发布。

## 包含内容

- `src/`：文章生成、图片生成、公众号草稿上传脚本
- `prompts/styles/`：文案风格模板
- `prompts/images/`：封面图和正文插图模板
- `configs/config.json.example`：公众号配置示例
- `examples/article_example.md`：上传测试用示例文章

## 安装依赖

建议使用 Python 3.10+：

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 公众号配置

先复制示例文件：

```bash
cp configs/config.json.example config.json
```

然后填入你自己的公众号 `app_id` 和 `app_secret`。

## 最小使用流程

1. 把原始素材放到 `data/inputs/subtitles/`
2. 用 `src/weixin_workflow.py` 生成文章
3. 为封面图和 2 张正文图准备 prompt
4. 用 `src/gen_image_gemini.py` 生成图片
5. 把图片相对路径插回 Markdown
6. 用 `src/wechat_api.py` 上传到公众号草稿箱

## 常用命令

生成文章：

```bash
python3 src/weixin_workflow.py \
  --subtitle podcast.txt \
  --style new-york-times \
  --non-interactive
```

如果文章已写好：

```bash
python3 src/weixin_workflow.py \
  --subtitle podcast.txt \
  --style new-york-times \
  --article-file data/outputs/articles/podcast-draft.md \
  --non-interactive
```

生成封面图：

```bash
python3 src/gen_image_gemini.py "你的封面 prompt" \
  -o data/outputs/images/cover.png
```

上传公众号草稿：

```bash
python3 src/wechat_api.py data/outputs/images/cover.png \
  -f data/outputs/articles/podcast.md \
  -t "文章标题"
```

## 说明

- `data/inputs/subtitles/` 和 `data/outputs/` 默认作为工作目录使用，但不建议把真实内容直接提交到 GitHub。
- 如果要公开发布，建议优先确认 `data/references/` 中的素材是否具备可公开分发权限。

## 如何获取公众号 AppID 和 AppSecret

本仓库不会提供任何公众号凭证。你需要使用自己的公众号后台信息。

获取方式：

1. 登录 [微信公众平台开发者中心](https://developers.weixin.qq.com/platform)
2. 进入你自己的公众号或开放平台相关后台
3. 在应用设置或开发设置中查看 `AppID` 和 `AppSecret`
4. 将它们填入本仓库根目录的 `config.json`

建议先复制示例配置：

```bash
cp configs/config.json.example config.json
```

然后再填写你自己的账号信息。不要把真实 `config.json` 提交到 GitHub。
