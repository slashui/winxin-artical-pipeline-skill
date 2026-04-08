import requests
import json
import re
from typing import Dict, Optional, List
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "config.json"


class WeChatPublicAPI:
    """微信公众号API客户端"""

    def __init__(self, app_id: str, app_secret: str):
        self.app_id = app_id
        self.app_secret = app_secret
        self.access_token: Optional[str] = None

    def get_access_token(self) -> str:
        """获取access_token"""
        url = "https://api.weixin.qq.com/cgi-bin/token"
        params = {
            "grant_type": "client_credential",
            "appid": self.app_id,
            "secret": self.app_secret
        }

        response = requests.get(url, params=params)
        result = response.json()

        if "access_token" in result:
            self.access_token = result["access_token"]
            return self.access_token
        else:
            raise Exception(f"获取access_token失败: {result}")

    def upload_image(self, image_path: str) -> str:
        """
        上传图片素材（永久素材）

        Args:
            image_path: 图片文件路径

        Returns:
            media_id
        """
        if not self.access_token:
            self.get_access_token()

        url = f"https://api.weixin.qq.com/cgi-bin/material/add_material?access_token={self.access_token}&type=image"

        with open(image_path, 'rb') as f:
            files = {'media': f}
            data = {'type': 'image'}
            response = requests.post(url, files=files, data=data)
            result = response.json()

        if "media_id" in result:
            return result["media_id"]
        else:
            raise Exception(f"上传图片失败: {result}")

    def upload_article_image(self, image_path: str) -> str:
        """
        上传图文消息内的图片（获取URL）

        Args:
            image_path: 图片文件路径

        Returns:
            图片URL
        """
        if not self.access_token:
            self.get_access_token()

        url = f"https://api.weixin.qq.com/cgi-bin/media/uploadimg?access_token={self.access_token}"

        with open(image_path, 'rb') as f:
            files = {'media': f}
            response = requests.post(url, files=files)
            result = response.json()

        if "url" in result:
            return result["url"]
        else:
            raise Exception(f"上传文章图片失败: {result}")

    def add_draft(self, title: str, content: str, author: str = "",
                  digest: str = "", thumb_media_id: str = "") -> Dict:
        """
        添加草稿

        Args:
            title: 文章标题
            content: 文章内容（HTML格式）
            author: 作者
            digest: 摘要
            thumb_media_id: 封面图片media_id（可选）

        Returns:
            API响应结果
        """
        if not self.access_token:
            self.get_access_token()

        url = f"https://api.weixin.qq.com/cgi-bin/draft/add?access_token={self.access_token}"

        # 将纯文本内容转换为HTML格式
        html_content = content.replace("\n", "<br/>")

        articles = {
            "articles": [{
                "title": title,
                "author": author,
                "digest": digest,
                "content": html_content,
                "content_source_url": "",
                "thumb_media_id": thumb_media_id,
                "need_open_comment": 0,
                "only_fans_can_comment": 0
            }]
        }

        # 确保中文不被转义
        headers = {'Content-Type': 'application/json; charset=utf-8'}
        data = json.dumps(articles, ensure_ascii=False).encode('utf-8')
        response = requests.post(url, data=data, headers=headers)
        result = response.json()

        return result


def markdown_to_html(content: str) -> str:
    """
    将简单Markdown转换为HTML

    Args:
        content: Markdown内容

    Returns:
        HTML内容
    """
    html = content

    # 标题
    html = re.sub(
        r'^# (.*?)$',
        r'<h1 style="font-size: 24px; font-weight: bold; color: #e65e2a; margin: 24px 0 12px 0; padding-bottom: 8px; border-bottom: 1px solid #eee;">\1</h1>',
        html, flags=re.MULTILINE)
    html = re.sub(
        r'^## (.*?)$',
        r'<h2 style="font-size: 20px; font-weight: bold; color: #e65e2a; margin: 20px 0 10px 0;">\1</h2>',
        html, flags=re.MULTILINE)
    html = re.sub(
        r'^### (.*?)$',
        r'<h3 style="font-size: 17px; font-weight: bold; color: #e65e2a; margin: 16px 0 8px 0;">\1</h3>',
        html, flags=re.MULTILINE)

    # 引用（blockquote）
    html = re.sub(
        r'^> (.*?)$',
        r'<blockquote style="border-left: 3px solid #e65e2a; padding: 10px 15px; margin: 16px 0; color: #555; background: #f9f9f9; font-style: italic;">\1</blockquote>',
        html, flags=re.MULTILINE)

    # 粗体
    html = re.sub(r'\*\*(.*?)\*\*', r'<strong style="font-weight: bold; color: #1a1a1a;">\1</strong>', html)

    # 斜体
    html = re.sub(r'\*(.*?)\*', r'<em>\1</em>', html)

    # 列表项
    html = re.sub(
        r'^- (.*?)$',
        r'<li style="margin: 4px 0;">\1</li>',
        html, flags=re.MULTILINE)

    # 包装连续的li为ul
    html = re.sub(
        r'(<li.*?</li>(\n<li.*?</li>)*)',
        r'<ul style="padding-left: 20px; margin: 10px 0;">\1</ul>',
        html, flags=re.DOTALL)

    # 段落（两个换行符之间的内容）
    paragraphs = html.split('\n\n')
    formatted_paragraphs = []
    for p in paragraphs:
        p = p.strip()
        if p and not p.startswith('<'):
            p = f'<p style="margin: 12px 0; text-align: justify;">{p}</p>'
        formatted_paragraphs.append(p)

    html = ''.join(formatted_paragraphs)

    # 单个换行符转为br
    html = html.replace('\n', '<br/>')

    # 添加样式
    styled_html = f'''
<section style="font-size: 16px; color: #333; line-height: 1.8; padding: 10px 0;">
{html}
</section>
    '''.strip()

    return styled_html


def read_file_content(file_path: str) -> str:
    """读取文件内容"""
    with open(file_path, 'r', encoding='utf-8') as f:
        return f.read()


def resolve_path(path_str: str) -> Path:
    """Resolve CLI file paths relative to the project root."""
    path = Path(path_str)
    if path.is_absolute():
        return path
    return (PROJECT_ROOT / path).resolve()


def load_account_config(config_path: Path, account_name: Optional[str]) -> Dict[str, str]:
    with config_path.open('r', encoding='utf-8') as f:
        config = json.load(f)

    if 'accounts' not in config:
        return config

    selected_account = account_name or config.get('default', '')
    if selected_account not in config['accounts']:
        available_accounts = ', '.join(config['accounts'].keys())
        raise KeyError(f"账号 '{selected_account}' 不存在，可用: {available_accounts}")

    print(f"使用账号: {selected_account}")
    return config['accounts'][selected_account]


def process_content_images(content: str, api: WeChatPublicAPI, base_path: str = ".") -> str:
    """
    处理内容中的图片引用，上传并替换为URL

    Args:
        content: 原始内容
        api: API客户端
        base_path: 图片文件基础路径

    Returns:
        处理后的内容
    """
    # 查找 ![alt](image_path) 格式的图片
    pattern = r'!\[([^\]]*)\]\(([^)]+)\)'

    def replace_image(match):
        alt_text = match.group(1)
        image_path = match.group(2)

        # 构建完整路径
        full_path = Path(base_path) / image_path
        if not full_path.exists():
            print(f"警告: 图片不存在 {full_path}")
            return match.group(0)

        try:
            print(f"正在上传文章图片: {full_path}")
            image_url = api.upload_article_image(str(full_path))
            print(f"图片上传成功: {image_url}")
            return f'<img src="{image_url}" alt="{alt_text}" style="max-width: 100%; height: auto;" />'
        except Exception as e:
            print(f"上传图片失败: {e}")
            return match.group(0)

    return re.sub(pattern, replace_image, content)


def send_to_draft(app_id: str, app_secret: str,
                  file_path: str, title: str = "草稿文章",
                  cover_image: Optional[str] = None,
                  use_markdown: bool = True) -> Dict:
    """
    发送文件内容到微信公众号草稿箱

    Args:
        app_id: 微信公众号AppID
        app_secret: 微信公众号AppSecret
        file_path: 要发送的文件路径
        title: 文章标题
        cover_image: 封面图片路径（必需）
        use_markdown: 是否将内容作为Markdown处理

    Returns:
        API响应结果
    """
    # 读取文件内容
    content = read_file_content(file_path)

    # 创建API客户端
    api = WeChatPublicAPI(app_id, app_secret)

    # 处理内容中的图片
    base_path = str(Path(file_path).parent)
    content = process_content_images(content, api, base_path)

    # 转换Markdown为HTML
    if use_markdown:
        content = markdown_to_html(content)

    # 上传封面图片
    if not cover_image:
        raise Exception("必须提供封面图片！")

    print(f"正在上传封面图片: {cover_image}")
    thumb_media_id = api.upload_image(cover_image)
    print(f"封面上传成功，media_id: {thumb_media_id}")

    # 发送到草稿箱
    result = api.add_draft(title=title, content=content, thumb_media_id=thumb_media_id)

    return result


if __name__ == "__main__":
    import argparse

    # 解析命令行参数
    parser = argparse.ArgumentParser(description='发送文章到微信公众号草稿箱')
    parser.add_argument('cover_image', help='封面图片路径')
    parser.add_argument(
        '-f',
        '--file',
        default='examples/article_example.md',
        help='文章内容文件路径（默认: examples/article_example.md）',
    )
    parser.add_argument('-t', '--title', default='草稿文章', help='文章标题（默认: 草稿文章）')
    parser.add_argument('--no-markdown', action='store_true', help='不使用Markdown格式')
    parser.add_argument('-a', '--account', default=None, help='公众号账号名称（如 account1、account2）')
    parser.add_argument(
        '-c',
        '--config',
        default=str(DEFAULT_CONFIG_PATH),
        help='配置文件路径（默认: config.json）',
    )

    args = parser.parse_args()

    # 从配置文件读取
    try:
        config_path = resolve_path(args.config)
        account = load_account_config(config_path, args.account)
        APP_ID = account['app_id']
        APP_SECRET = account['app_secret']
    except FileNotFoundError:
        print(f"请先创建配置文件: {resolve_path(args.config)}")
        raise SystemExit(1)
    except KeyError as exc:
        print(str(exc))
        raise SystemExit(1)
    except json.JSONDecodeError as exc:
        print(f"配置文件格式错误: {exc}")
        exit(1)

    # 发送文件到草稿箱
    result = send_to_draft(
        app_id=APP_ID,
        app_secret=APP_SECRET,
        file_path=str(resolve_path(args.file)),
        title=args.title,
        cover_image=str(resolve_path(args.cover_image)),
        use_markdown=not args.no_markdown
    )

    if "media_id" in result:
        print("\n✓ 发送成功！")
        print(f"草稿 media_id: {result['media_id']}")
    else:
        print("\n✗ 发送失败:")
        print(json.dumps(result, ensure_ascii=False, indent=2))
