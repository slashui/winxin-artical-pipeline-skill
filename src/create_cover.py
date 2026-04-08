"""创建默认封面图片"""
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path


DEFAULT_OUTPUT_PATH = Path(__file__).resolve().parent.parent / "data" / "outputs" / "images" / "cover.jpg"


def create_default_cover(output_path: str = str(DEFAULT_OUTPUT_PATH),
                         width: int = 900, height: int = 500) -> None:
    """
    创建默认封面图片

    Args:
        output_path: 输出文件路径
        width: 图片宽度
        height: 图片高度
    """
    # 创建图片
    img = Image.new('RGB', (width, height), color='#4A90E2')

    # 绘制文字
    draw = ImageDraw.Draw(img)

    # 尝试使用系统字体
    try:
        # macOS 中文字体
        font_large = ImageFont.truetype('/System/Library/Fonts/STHeiti Light.ttc', 80)
        font_small = ImageFont.truetype('/System/Library/Fonts/STHeiti Light.ttc', 40)
    except:
        try:
            # 尝试其他中文字体
            font_large = ImageFont.truetype('/System/Library/Fonts/PingFang.ttc', 80)
            font_small = ImageFont.truetype('/System/Library/Fonts/PingFang.ttc', 40)
        except:
            # 如果没有中文字体，使用默认字体
            font_large = ImageFont.load_default()
            font_small = ImageFont.load_default()

    # 绘制标题
    text1 = "微信公众号"
    text2 = "文章封面"

    # 计算文字位置（居中）
    bbox1 = draw.textbbox((0, 0), text1, font=font_large)
    bbox2 = draw.textbbox((0, 0), text2, font=font_small)

    text1_width = bbox1[2] - bbox1[0]
    text2_width = bbox2[2] - bbox2[0]

    x1 = (width - text1_width) // 2
    y1 = height // 2 - 60

    x2 = (width - text2_width) // 2
    y2 = height // 2 + 20

    draw.text((x1, y1), text1, fill='white', font=font_large)
    draw.text((x2, y2), text2, fill='white', font=font_small)

    # 保存图片
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    img.save(output_file, 'JPEG', quality=95)
    print(f"封面图片已创建: {output_file}")


if __name__ == "__main__":
    create_default_cover()
