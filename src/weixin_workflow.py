"""Interactive workflow for selecting input material and generating article drafts."""
from __future__ import annotations

import argparse
import json
import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional

import requests


PROJECT_ROOT = Path(__file__).resolve().parent.parent
SUBTITLE_DIR = PROJECT_ROOT / "data" / "inputs" / "subtitles"
STYLE_DIR = PROJECT_ROOT / "prompts" / "styles"
ARTICLE_DIR = PROJECT_ROOT / "data" / "outputs" / "articles"

TEXT_FILE_SUFFIXES = {
    ".txt",
    ".md",
    ".markdown",
    ".srt",
    ".vtt",
}


@dataclass(frozen=True)
class WorkflowSelection:
    subtitle_file: Path
    style_file: Path


def list_candidate_files(directory: Path, suffixes: Optional[Iterable[str]] = None) -> List[Path]:
    if not directory.exists():
        return []

    allowed = {suffix.lower() for suffix in suffixes or []}
    files: List[Path] = []
    for path in sorted(directory.iterdir()):
        if not path.is_file() or path.name.startswith("."):
            continue
        if allowed and path.suffix.lower() not in allowed:
            continue
        files.append(path)
    return files


def prompt_choice(paths: List[Path], label: str) -> Path:
    if not paths:
        raise FileNotFoundError(f"没有可选的{label}文件")

    if len(paths) == 1:
        selected = paths[0]
        print(f"只找到一个{label}，自动选择: {selected.name}")
        return selected

    print(f"请选择{label}:")
    for index, path in enumerate(paths, start=1):
        print(f"  {index}. {path.name}")

    while True:
        raw = input(f"输入{label}序号: ").strip()
        if not raw.isdigit():
            print("请输入数字序号。")
            continue
        choice = int(raw)
        if 1 <= choice <= len(paths):
            return paths[choice - 1]
        print("序号超出范围，请重新输入。")


def resolve_selected_file(directory: Path, value: Optional[str], suffixes: Optional[Iterable[str]] = None) -> Optional[Path]:
    if not value:
        return None

    candidate = Path(value)
    if not candidate.is_absolute():
        candidate = directory / value
    if candidate.exists():
        return candidate.resolve()

    matches = [path for path in list_candidate_files(directory, suffixes) if path.stem == value or path.name == value]
    if len(matches) == 1:
        return matches[0].resolve()

    raise FileNotFoundError(f"找不到指定文件: {value}")


def select_inputs(subtitle_name: Optional[str], style_name: Optional[str], interactive: bool) -> WorkflowSelection:
    subtitle_files = list_candidate_files(SUBTITLE_DIR, TEXT_FILE_SUFFIXES)
    style_files = list_candidate_files(STYLE_DIR, {".md"})

    subtitle_file = resolve_selected_file(SUBTITLE_DIR, subtitle_name, TEXT_FILE_SUFFIXES)
    style_file = resolve_selected_file(STYLE_DIR, style_name, {".md"})

    if subtitle_file is None:
        if len(subtitle_files) == 1:
            subtitle_file = subtitle_files[0].resolve()
        elif not interactive:
            raise ValueError("存在多个字幕文件时，非交互模式必须通过 --subtitle 指定。")
        else:
            subtitle_file = prompt_choice(subtitle_files, "字幕文件")

    if style_file is None:
        if len(style_files) == 1:
            style_file = style_files[0].resolve()
        elif not interactive:
            raise ValueError("存在多个写作风格时，非交互模式必须通过 --style 指定。")
        else:
            style_file = prompt_choice(style_files, "写作风格")

    return WorkflowSelection(subtitle_file=subtitle_file, style_file=style_file)


def build_messages(style_prompt: str, subtitle_path: Path, subtitle_content: str) -> List[dict]:
    system_prompt = (
        "你是一个专业的中文公众号写作助手。"
        "请严格遵守给定写作风格，直接输出最终 Markdown 成稿，不要输出解释、分析过程或额外说明。\n\n"
        f"{style_prompt.strip()}"
    )
    user_prompt = (
        f"请根据以下字幕/素材生成一篇适合发布到微信公众号的 Markdown 文章。\n"
        f"- 原始文件名: {subtitle_path.name}\n"
        f"- 输出要求: 保存为完整 Markdown 成稿，第一行必须是一级标题。\n"
        f"- 如果原文没有清晰大纲，请你自行提炼结构。\n"
        f"- 默认用中文写作，保留必要的人名、产品名、英文术语。\n\n"
        "以下是原始字幕/素材：\n"
        f"{subtitle_content.strip()}"
    )
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]


def call_text_model(messages: List[dict]) -> str:
    api_base = os.getenv("WEIXIN_LLM_API_BASE") or os.getenv("OPENAI_BASE_URL")
    api_key = os.getenv("WEIXIN_LLM_API_KEY") or os.getenv("OPENAI_API_KEY")
    model = os.getenv("WEIXIN_LLM_MODEL") or os.getenv("OPENAI_MODEL")

    if not api_base or not api_key or not model:
        raise RuntimeError(
            "缺少文本生成配置。请设置 WEIXIN_LLM_API_BASE、WEIXIN_LLM_API_KEY、WEIXIN_LLM_MODEL。"
        )

    url = api_base.rstrip("/") + "/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }
    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.8,
    }

    response = requests.post(url, headers=headers, json=payload, timeout=180)
    response.raise_for_status()
    data = response.json()

    try:
        return data["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError, TypeError) as exc:
        raise RuntimeError(f"模型返回结构异常: {json.dumps(data, ensure_ascii=False)}") from exc


def write_article(output_path: Path, content: str) -> Path:
    ARTICLE_DIR.mkdir(parents=True, exist_ok=True)
    output_path.write_text(content.rstrip() + "\n", encoding="utf-8")
    return output_path


def validate_article_markdown(content: str) -> None:
    stripped = content.lstrip()
    if not stripped.startswith("# "):
        raise ValueError("文章内容必须是 Markdown 成稿，且第一行必须是一级标题。")


def copy_existing_article(article_file: Path, output_path: Path) -> Path:
    content = article_file.read_text(encoding="utf-8")
    validate_article_markdown(content)
    ARTICLE_DIR.mkdir(parents=True, exist_ok=True)
    if article_file.resolve() == output_path.resolve():
        output_path.write_text(content.rstrip() + "\n", encoding="utf-8")
        return output_path
    shutil.copyfile(article_file, output_path)
    return output_path


def generate_article(selection: WorkflowSelection, article_file: Optional[Path] = None) -> Path:
    output_path = ARTICLE_DIR / f"{selection.subtitle_file.stem}.md"
    if article_file is not None:
        return copy_existing_article(article_file, output_path)

    subtitle_content = selection.subtitle_file.read_text(encoding="utf-8")
    style_prompt = selection.style_file.read_text(encoding="utf-8")
    messages = build_messages(style_prompt, selection.subtitle_file, subtitle_content)
    article = call_text_model(messages)
    return write_article(output_path, article)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="微信公众号文章生成工作流")
    parser.add_argument("--subtitle", help="指定字幕文件名或路径")
    parser.add_argument("--style", help="指定写作风格文件名、路径或 style stem")
    parser.add_argument(
        "--article-file",
        help="使用已经写好的 Markdown 文章文件，跳过文本 API 生成并复制到输出目录。",
    )
    parser.add_argument(
        "--non-interactive",
        action="store_true",
        help="关闭交互式选择；必须显式指定字幕和风格",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    selection = select_inputs(
        subtitle_name=args.subtitle,
        style_name=args.style,
        interactive=not args.non_interactive,
    )
    article_file = None
    if args.article_file:
        article_file = Path(args.article_file)
        if not article_file.is_absolute():
            article_file = (PROJECT_ROOT / article_file).resolve()
        if not article_file.exists():
            raise FileNotFoundError(f"找不到文章文件: {article_file}")

    print(f"已选择字幕: {selection.subtitle_file.name}")
    print(f"已选择风格: {selection.style_file.stem}")
    if article_file:
        print(f"使用现成文章: {article_file}")

    article_path = generate_article(selection, article_file=article_file)
    print(f"文章已生成: {article_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
