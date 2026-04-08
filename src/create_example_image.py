"""创建示例图片用于测试"""
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path


DEFAULT_OUTPUT_PATH = Path(__file__).resolve().parent.parent / "data" / "outputs" / "images" / "example.jpg"


def create_example_image(output_path: str = str(DEFAULT_OUTPUT_PATH),
                         width: int = 600, height: int = 400) -> None:
    """
    创建示例图片

    Args:
        output_path: 输出文件路径
        width: 图片宽度
        height: 图片高度
    """
    # 创建渐变背景
    img = Image.new('RGB', (width, height))
    draw = ImageDraw.Draw(img)

    # 绘制渐变背景
    for y in range(height):
        r = int(74 + (144 - 74) * y / height)
        g = int(144 + (224 - 144) * y / height)
        b = int(226 + (255 - 226) * y / height)
        draw.line([(0, y), (width, y)], fill=(r, g, b))

    # 添加文字
    try:
        font = ImageFont.truetype('/System/Library/Fonts/STHeiti Light.ttc', 50)
    except:
        try:
            font = ImageFont.truetype('/System/Library/Fonts/PingFang.ttc', 50)
        except:
            font = ImageFont.load_default()

    text = "示例图片"
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]

    x = (width - text_width) // 2
    y = (height - text_height) // 2

    # 添加阴影
    draw.text((x + 2, y + 2), text, fill=(0, 0, 0, 128), font=font)
    # 主文字
    draw.text((x, y), text, fill='white', font=font)

    # 保存
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    img.save(output_file, 'JPEG', quality=95)
    print(f"示例图片已创建: {output_file}")


if __name__ == "__main__":
    create_example_image()
