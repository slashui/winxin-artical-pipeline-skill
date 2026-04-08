---
name: weixin-article-pipeline
description: Turn raw notes, subtitles, transcripts, or source material into a publishable WeChat Official Account article, decide where inline images should be inserted, generate the cover and inline images, and upload the result to the WeChat draft box. Use when working in this repository and the task involves rewriting material into a 公众号文章, planning 插图位置, generating 公众号配图, or uploading a finished article into 微信公众号草稿箱.
---

# Weixin Article Pipeline

Use this skill as the execution guide for the existing repository workflow. Reuse the repository scripts instead of re-implementing article writing, image generation, or WeChat draft upload logic.

## Preconditions

Work from the repository root.

Check these inputs before starting:

- Source material exists in `data/inputs/subtitles/`, or can be added there first.
- A writing style exists in `prompts/styles/`, or the user explicitly asks for a new one.
- If article writing will be generated through the repository text model flow, the required env vars are set:
  - `WEIXIN_LLM_API_BASE` or `OPENAI_BASE_URL`
  - `WEIXIN_LLM_API_KEY` or `OPENAI_API_KEY`
  - `WEIXIN_LLM_MODEL` or `OPENAI_MODEL`
- If the article is already written by the user or Codex and saved as Markdown, those text env vars are not required.
- Gemini image generation env vars are set:
  - one of `GEMINI_API_KEY`, `GOOGLE_API_KEY`, or `GOOGLE_GENAI_API_KEY`
  - optionally `GEMINI_API_BASE`
  - optionally `GEMINI_IMAGE_MODEL`
- WeChat account config exists at `config.json`.

If any required config is missing, stop and say exactly what is missing instead of running a partial publishing flow.

## Core Workflow

### 1. Resolve the source file and style

Prefer the existing repository entrypoint:

```bash
python3 src/weixin_workflow.py --subtitle <file> --style <style> --non-interactive
```

If the article is already written as Markdown, hand it to the workflow with:

```bash
python3 src/weixin_workflow.py --subtitle <file> --style <style> --article-file <article-md> --non-interactive
```

Use interactive mode only when the user explicitly wants to choose from a list.

The article output lands in `data/outputs/articles/<stem>.md`.

### 2. Read the article and plan image placement

Do not generate images immediately after the article exists. First read the article and decide:

- one cover image concept
- two inline image placements

For each inline image, define:

- purpose
- insertion point
- what the reader should understand at a glance
- final generation prompt

Apply these rules:

- Insert images only where they improve comprehension or compress a multi-point explanation.
- At least one inline image should function like a summary slide for the section that follows.
- Avoid decorative images that do not carry information.
- Favor editorial illustration or clean infographic composition suitable for 公众号阅读.
- Use Simplified Chinese only when visible labels are actually needed.
- Keep images horizontal and suitable for a 16:9 crop.

Write the image plan next to the article as `data/outputs/articles/<stem>-image-prompts.md`.

### 3. Generate inline images and insert them back into the article

Generate the two inline images with `src/gen_image_gemini.py` and save them under `data/outputs/images/` with stable names such as:

- `data/outputs/images/<stem>-01.png`
- `data/outputs/images/<stem>-02.png`

If no Gemini key is present, stop and ask the user for one. Do not silently switch to another image backend unless the user explicitly asks for that.

Then insert Markdown image references into the article:

```md
![图片说明](../images/<stem>-01.png)
```

Keep each image on its own paragraph and place it exactly where the plan says.

### 4. Generate the cover image

Generate the cover after the article and inline image plan are stable. Save it to:

```text
data/outputs/images/cover.png
```

The cover should emphasize tension, contrast, hook, or story energy. Do not make the cover a literal summary slide.

### 5. Upload to the WeChat draft box

After the article contains final local image references and `cover.png` exists, upload with:

```bash
python3 src/wechat_api.py data/outputs/images/cover.png \
  -f data/outputs/articles/<stem>.md \
  -t "<title>" \
  [-a <account-name>]
```

`src/wechat_api.py` uploads inline images referenced in the Markdown, converts the body to HTML, uploads the cover, and creates the draft entry.

## Execution Rules

- Prefer existing repo commands over ad hoc scripts.
- Keep file paths repo-relative when running commands from the repository root.
- Do not claim the draft upload succeeded unless the command returns a success result containing a `media_id`.
- If the user only asks for the skill, create or update the skill file; do not run the publishing pipeline without being asked.
- If the user asks to run the pipeline, report the concrete artifact paths you produced.
- Do not require any older image backend unless the user explicitly asks for it.

## References

Read `README.md` and the relevant files under `src/`, `prompts/`, and `configs/` when you need the exact commands, file layout, or image-planning conventions.
