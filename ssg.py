"""静态博客生成器"""

import re
import base64
import shutil
import markdown
from pathlib import Path
from typing import Dict, Any, Tuple, List
from jinja2 import Environment, FileSystemLoader, select_autoescape

CONFIG: Dict[str, str] = {"author": "安静", "url": "https://anjing.art"}

BASE_DIR = Path(__file__).parent
SRC_DIR = BASE_DIR / "src"
CONTENT_DIR = SRC_DIR / "content"
POSTS_DIR = CONTENT_DIR / "posts"
PUBLISH_DIR = BASE_DIR / "publish"

# Jinja2 模板环境（全局单例，避免重复创建）
jinja_env = Environment(
    loader=FileSystemLoader(SRC_DIR / "layouts"),
    autoescape=select_autoescape(["html", "xml"]),
)

FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)


def parse_frontmatter(text: str) -> Tuple[Dict[str, str], str]:
    """解析 frontmatter，返回 (元数据字典, 正文)"""
    match = FRONTMATTER_RE.match(text)
    if not match:
        return {}, text

    meta = {}
    for line in match.group(1).splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            meta[key.strip()] = value.strip()
    return meta, text[match.end() :]


def title_to_url(title: str) -> str:
    """标题 → Base64 URL 安全编码，用作文件名"""
    encoded = base64.urlsafe_b64encode(title.encode()).decode()
    return encoded.rstrip("=") + ".html"


def parse_post(filepath: Path) -> Dict[str, Any]:
    """解析 Markdown 文件，返回文章字典（含 title/date/draft/content）"""
    text = filepath.read_text(encoding="utf-8")
    meta, body = parse_frontmatter(text)
    html = markdown.Markdown(extensions=["extra"]).convert(body)

    return {
        "title": meta.get("title", "Untitled"),
        "created": meta.get("created", ""),
        "updated": meta.get("updated", ""),
        "draft": meta.get("draft", "false").lower() == "true",
        "content": html,
    }


def render_to_file(
    template_name: str, context: Dict[str, Any], output_path: Path
) -> None:
    """渲染模板并写入文件"""
    html = jinja_env.get_template(template_name).render(context)
    output_path.write_text(html, encoding="utf-8")


def copy_resources(src: Path, dest: Path, dirs: List[str]) -> None:
    """复制静态资源目录"""
    for dirname in dirs:
        src_dir = src / dirname
        dest_dir = dest / dirname
        dest_dir.mkdir(parents=True, exist_ok=True)
        if src_dir.exists():
            for f in src_dir.iterdir():
                if f.is_file():
                    shutil.copy(f, dest_dir / f.name)


def build() -> None:
    """构建静态博客"""
    # 清空输出目录（保留目录本身）
    if PUBLISH_DIR.exists():
        for item in PUBLISH_DIR.iterdir():
            if item.is_file():
                item.unlink()
            elif item.is_dir():
                shutil.rmtree(item)
    else:
        PUBLISH_DIR.mkdir(parents=True)

    # 复制静态资源
    copy_resources(SRC_DIR, PUBLISH_DIR, ["styles", "images", "fonts"])
    (PUBLISH_DIR / "posts").mkdir(parents=True, exist_ok=True)

    # 解析文章：过滤草稿，按日期倒序
    posts: List[Dict[str, Any]] = []
    for md_file in POSTS_DIR.glob("*.md"):
        post = parse_post(md_file)
        if not post["draft"]:
            post["url"] = title_to_url(post["title"])
            posts.append(post)
    posts.sort(key=lambda p: p["created"], reverse=True)

    ctx = {"config": CONFIG, "posts": posts}

    # 生成首页
    render_to_file("index.html", ctx, PUBLISH_DIR / "index.html")

    # 生成文章页
    for post in posts:
        render_to_file(
            "article.html",
            {"config": CONFIG, "post": post},
            PUBLISH_DIR / "posts" / post["url"],
        )

    # 生成关于页
    about_md = CONTENT_DIR / "about.md"
    if about_md.exists():
        page = parse_post(about_md)
        if not page["draft"]:
            render_to_file(
                "article.html",
                {"config": CONFIG, "post": page},
                PUBLISH_DIR / "about.html",
            )

    print(f"构建完成！共 {len(posts)} 篇文章 → {PUBLISH_DIR}")


if __name__ == "__main__":
    build()
