"""通过 API 生成图像"""
import argparse
import base64
import mimetypes
import os
import re
from pathlib import Path
from typing import Optional

import requests
from PIL import Image


DEFAULT_API_URL = "https://zeakai-api.api4midjourney.com/v1/chat/completions"
DEFAULT_MODEL = "gemini-3-pro-image-preview"
PROJECT_ROOT = Path(__file__).resolve().parent.parent
IMAGE_DIR = PROJECT_ROOT / "data" / "outputs" / "images"
DEFAULT_OUTPUT_PATH = IMAGE_DIR / "cover.png"
DEFAULT_CROP_RATIO = "16:9"


def encode_image_as_data_url(image_path: Path) -> str:
    """把本地图片编码成 data URL，便于图生图接口直接读取。"""
    if not image_path.exists():
        raise FileNotFoundError(f"参考图不存在: {image_path}")

    mime_type, _ = mimetypes.guess_type(image_path.name)
    if not mime_type:
        mime_type = "application/octet-stream"

    encoded = base64.b64encode(image_path.read_bytes()).decode("ascii")
    return f"data:{mime_type};base64,{encoded}"


def parse_ratio(ratio_text: str) -> float:
    """把 '16:9' 这类比例转成浮点数。"""
    raw = ratio_text.strip()
    if ":" in raw:
        left, right = raw.split(":", 1)
        return float(left) / float(right)
    return float(raw)


def gen_image(
    prompt: str,
    output_path: Optional[str] = None,
    reference_image: Optional[str] = None,
    crop_ratio: str = DEFAULT_CROP_RATIO,
) -> str:
    """
    调用 API 生成图像并保存到本地

    Args:
        prompt: 图像描述
        output_path: 输出文件路径，不指定则自动生成
        reference_image: 可选的参考图路径，用于图生图
        crop_ratio: 输出裁剪比例，默认 16:9；传 none/off 可关闭裁剪

    Returns:
        保存的文件路径
    """
    api_key = os.getenv("WEIXIN_IMAGE_API_KEY")
    if not api_key:
        raise RuntimeError("缺少图像生成配置。请设置 WEIXIN_IMAGE_API_KEY。")
    api_url = os.getenv("WEIXIN_IMAGE_API_URL", DEFAULT_API_URL)
    model = os.getenv("WEIXIN_IMAGE_MODEL", DEFAULT_MODEL)

    headers = {
        "Content-Type": "application/json",
        "Authorization": api_key,
    }

    user_content: object = prompt
    if reference_image:
        reference_path = Path(reference_image).expanduser().resolve()
        user_content = [
            {"type": "text", "text": prompt},
            {
                "type": "image_url",
                "image_url": {
                    "url": encode_image_as_data_url(reference_path),
                },
            },
        ]

    payload = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": user_content,
            }
        ],
        "stream": False,
    }

    print(f"正在生成图像: {prompt}")
    if reference_image:
        print(f"参考图: {Path(reference_image).expanduser().resolve()}")
    response = requests.post(api_url, headers=headers, json=payload, timeout=120)
    response.raise_for_status()

    result = response.json()

    # 从返回内容中提取图片 URL
    content = result["choices"][0]["message"]["content"]
    match = re.search(r'!\[.*?\]\((https?://[^\s)]+)\)', content)

    if not match:
        raise Exception(f"未找到图片 URL，返回内容: {content}")

    image_url = match.group(1)
    print(f"图片 URL: {image_url}")

    # 下载图片
    img_response = requests.get(image_url, timeout=60)
    img_response.raise_for_status()

    # 生成输出路径
    if not output_path:
        output_path = str(DEFAULT_OUTPUT_PATH)
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, "wb") as f:
        f.write(img_response.content)

    ratio_flag = crop_ratio.strip().lower()
    if ratio_flag not in {"none", "off", "false", "0"}:
        img = Image.open(output_file)
        w, h = img.size
        target_ratio = parse_ratio(crop_ratio)
        current_ratio = w / h

        if abs(current_ratio - target_ratio) > 0.01:
            if current_ratio > target_ratio:
                new_w = int(h * target_ratio)
                left = (w - new_w) // 2
                img = img.crop((left, 0, left + new_w, h))
            else:
                new_h = int(w / target_ratio)
                top = (h - new_h) // 2
                img = img.crop((0, top, w, top + new_h))
            img.save(output_file)
            print(f"已裁剪为 {crop_ratio} ({img.size[0]}x{img.size[1]})")

    print(f"图片已保存: {output_file}")
    return str(output_file)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="生成图像")
    parser.add_argument("prompt", help="图像描述")
    parser.add_argument("-o", "--output", default=None, help="输出文件路径")
    parser.add_argument(
        "-i",
        "--reference-image",
        default=None,
        help="参考图路径。传入本地图片后会按图生图方式请求模型。",
    )
    parser.add_argument(
        "--crop-ratio",
        default=DEFAULT_CROP_RATIO,
        help="输出裁剪比例，默认 16:9；可传 2.35:1，或传 none 关闭裁剪。",
    )

    args = parser.parse_args()
    gen_image(
        args.prompt,
        args.output,
        reference_image=args.reference_image,
        crop_ratio=args.crop_ratio,
    )
