"""Use the official Gemini API to generate an image from a prompt."""

from __future__ import annotations

import argparse
import base64
import mimetypes
import os
from pathlib import Path
from typing import Optional

import requests


PROJECT_ROOT = Path(__file__).resolve().parent.parent
IMAGE_DIR = PROJECT_ROOT / "data" / "outputs" / "images"
DEFAULT_OUTPUT_PATH = IMAGE_DIR / "gemini-generated.png"
DEFAULT_MODEL = "gemini-3.1-flash-image-preview"
DEFAULT_API_BASE = "https://generativelanguage.googleapis.com/v1beta"
DEFAULT_ASPECT_RATIO = "16:9"
DEFAULT_IMAGE_SIZE = "2K"


def encode_file_as_inline_data(image_path: Path) -> dict:
    if not image_path.exists():
        raise FileNotFoundError(f"参考图不存在: {image_path}")

    mime_type, _ = mimetypes.guess_type(image_path.name)
    if not mime_type:
        mime_type = "application/octet-stream"

    return {
        "inline_data": {
            "mime_type": mime_type,
            "data": base64.b64encode(image_path.read_bytes()).decode("ascii"),
        }
    }


def extract_first_image_bytes(payload: dict) -> bytes:
    candidates = payload.get("candidates") or []
    for candidate in candidates:
        content = candidate.get("content") or {}
        for part in content.get("parts") or []:
            inline = part.get("inline_data") or part.get("inlineData")
            if inline and inline.get("data"):
                return base64.b64decode(inline["data"])
    raise RuntimeError(f"Gemini 未返回图片数据: {payload}")


def generate_image(
    prompt: str,
    output_path: Optional[str] = None,
    model: str = DEFAULT_MODEL,
    aspect_ratio: str = DEFAULT_ASPECT_RATIO,
    image_size: str = DEFAULT_IMAGE_SIZE,
    reference_image: Optional[str] = None,
) -> str:
    api_key = (
        os.getenv("GEMINI_API_KEY")
        or os.getenv("GOOGLE_API_KEY")
        or os.getenv("GOOGLE_GENAI_API_KEY")
    )
    if not api_key:
        raise RuntimeError(
            "缺少 Gemini API Key。请设置 GEMINI_API_KEY、GOOGLE_API_KEY 或 GOOGLE_GENAI_API_KEY。"
        )

    api_base = os.getenv("GEMINI_API_BASE", DEFAULT_API_BASE).rstrip("/")
    url = f"{api_base}/models/{model}:generateContent"

    parts = [{"text": prompt}]
    if reference_image:
        parts.append(encode_file_as_inline_data(Path(reference_image).expanduser().resolve()))

    payload = {
        "contents": [{"role": "user", "parts": parts}],
        "generationConfig": {
            "responseModalities": ["TEXT", "IMAGE"],
            "imageConfig": {
                "aspectRatio": aspect_ratio,
                "imageSize": image_size,
            },
        },
    }

    headers = {
        "Content-Type": "application/json",
        "x-goog-api-key": api_key,
    }

    print(f"正在调用 Gemini 生图模型: {model}")
    print(f"Prompt: {prompt}")
    if reference_image:
        print(f"参考图: {Path(reference_image).expanduser().resolve()}")

    response = requests.post(url, headers=headers, json=payload, timeout=180)
    response.raise_for_status()
    result = response.json()

    image_bytes = extract_first_image_bytes(result)

    destination = Path(output_path or DEFAULT_OUTPUT_PATH)
    if not destination.is_absolute():
        destination = (PROJECT_ROOT / destination).resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(image_bytes)

    print(f"图片已保存: {destination}")
    return str(destination)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="使用 Gemini 官方 API 根据 prompt 生成图片")
    parser.add_argument("prompt", help="生图 prompt")
    parser.add_argument("-o", "--output", default=str(DEFAULT_OUTPUT_PATH), help="输出文件路径")
    parser.add_argument(
        "-m",
        "--model",
        default=os.getenv("GEMINI_IMAGE_MODEL", DEFAULT_MODEL),
        help=f"Gemini 生图模型，默认 {DEFAULT_MODEL}",
    )
    parser.add_argument(
        "--aspect-ratio",
        default=DEFAULT_ASPECT_RATIO,
        help=f"图片比例，默认 {DEFAULT_ASPECT_RATIO}",
    )
    parser.add_argument(
        "--image-size",
        default=DEFAULT_IMAGE_SIZE,
        help=f"图片尺寸档位，默认 {DEFAULT_IMAGE_SIZE}",
    )
    parser.add_argument(
        "-i",
        "--reference-image",
        default=None,
        help="可选参考图路径，用于图生图或风格约束",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    generate_image(
        prompt=args.prompt,
        output_path=args.output,
        model=args.model,
        aspect_ratio=args.aspect_ratio,
        image_size=args.image_size,
        reference_image=args.reference_image,
    )
