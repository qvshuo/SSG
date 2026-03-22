"""静态博客生成器"""

import re
import shutil
import sys
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

# Jinja2 模板环境
jinja_env = Environment(
    loader=FileSystemLoader(SRC_DIR / "layouts"),
    autoescape=select_autoescape(["html", "xml"]),
    trim_blocks=True,
    lstrip_blocks=True,
)

FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)


def parse_frontmatter(text: str) -> Tuple[Dict[str, str], str]:
    """解析 frontmatter（仅支持单行 key: value 格式）"""
    match = FRONTMATTER_RE.match(text)
    if not match:
        return {}, text

    meta = {}
    for line in match.group(1).splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            meta[key.strip()] = value.strip()
    return meta, text[match.end() :]


def normalize_date(s: str) -> str:
    """统一日期分隔符为 '-'"""
    return s.replace("/", "-")


def parse_markdown(filepath: Path) -> Dict[str, Any]:
    """解析 Markdown 文件，返回页面字典（含 title/created/updated/draft/content）"""
    try:
        text = filepath.read_text(encoding="utf-8")
    except FileNotFoundError:
        print(f"错误：文件不存在 - {filepath}", file=sys.stderr)
        sys.exit(1)
    except UnicodeDecodeError as e:
        print(f"错误：文件编码错误 - {filepath}: {e}", file=sys.stderr)
        sys.exit(1)

    meta, body = parse_frontmatter(text)
    html = markdown.Markdown(extensions=["extra"]).convert(body)
    html = re.sub(r"<img(?![^>]*loading=)", r'<img loading="lazy" ', html)

    return {
        "title": meta.get("title", "Untitled"),
        "created": normalize_date(meta.get("created", "")),
        "updated": normalize_date(meta.get("updated", "")),
        "draft": meta.get("draft", "false").lower() == "true",
        "content": html,
    }


def post_url(filepath: Path) -> str:
    """用文件名（不含扩展名）作为 URL slug"""
    return filepath.stem + ".html"


def render_to_file(
    template_name: str, context: Dict[str, Any], output_path: Path
) -> None:
    """渲染模板并写入文件"""
    try:
        html = jinja_env.get_template(template_name).render(context)
        output_path.write_text(html, encoding="utf-8")
    except Exception as e:
        print(f"错误：渲染模板失败 - {template_name}: {e}", file=sys.stderr)
        sys.exit(1)


def clean_output_dir(path: Path) -> None:
    """清空输出目录（保留目录本身）"""
    if not path.exists():
        path.mkdir(parents=True)
        return

    for item in path.iterdir():
        if item.is_file():
            item.unlink()
        elif item.is_dir():
            shutil.rmtree(item)


def copy_resources(src: Path, dest: Path, dirs: List[str]) -> None:
    """复制静态资源目录（含子目录）"""
    for name in dirs:
        src_dir = src / name
        if src_dir.exists():
            shutil.copytree(src_dir, dest / name, dirs_exist_ok=True)


def build_sitemap(
    base_url: str, posts: List[Dict[str, Any]], standalone_pages: List[Dict[str, Any]]
) -> List[Dict[str, str]]:
    """构建 Sitemap 数据"""
    pages = []

    # 首页
    latest = posts[0] if posts else None
    index_lastmod = (latest["updated"] or latest["created"]) if latest else ""
    pages.append({"loc": f"{base_url}/", "lastmod": index_lastmod})

    # 文章页
    for post in posts:
        pages.append(
            {
                "loc": f"{base_url}/posts/{post['url']}",
                "lastmod": (post["updated"] or post["created"]),
            }
        )

    # 独立页面
    for page in standalone_pages:
        pages.append(
            {
                "loc": f"{base_url}/{page['url']}",
                "lastmod": (page["updated"] or page["created"]),
            }
        )

    return pages


def build() -> None:
    """构建静态博客"""
    # 检查必要的输入目录
    if not POSTS_DIR.exists():
        print(f"错误：文章目录不存在 - {POSTS_DIR}", file=sys.stderr)
        sys.exit(1)

    # 清空输出目录
    clean_output_dir(PUBLISH_DIR)

    # 复制静态资源
    copy_resources(SRC_DIR, PUBLISH_DIR, ["styles", "images", "fonts"])
    (PUBLISH_DIR / "posts").mkdir(parents=True, exist_ok=True)

    # 解析文章：过滤草稿，按日期倒序
    posts: List[Dict[str, Any]] = []
    md_files = list(POSTS_DIR.glob("*.md"))
    if not md_files:
        print("警告：未找到任何文章")

    for md_file in md_files:
        post = parse_markdown(md_file)
        if not post["draft"]:
            post["url"] = post_url(md_file)
            posts.append(post)

    posts.sort(key=lambda p: p["created"], reverse=True)

    # 渲染首页
    index_context = {"config": CONFIG, "posts": posts}
    render_to_file("index.html", index_context, PUBLISH_DIR / "index.html")

    # 渲染文章页
    for post in posts:
        render_to_file(
            "article.html",
            {"config": CONFIG, "post": post},
            PUBLISH_DIR / "posts" / post["url"],
        )

    # 渲染独立页面
    standalone_pages: List[Dict[str, Any]] = []
    about_md = CONTENT_DIR / "about.md"
    if about_md.exists():
        page = parse_markdown(about_md)
        if not page["draft"]:
            page["url"] = "about.html"
            standalone_pages.append(page)
            render_to_file(
                "article.html",
                {"config": CONFIG, "post": page},
                PUBLISH_DIR / "about.html",
            )

    # 生成 Sitemap
    base_url = CONFIG["url"].rstrip("/")
    sitemap_pages = build_sitemap(base_url, posts, standalone_pages)
    render_to_file("sitemap.xml", {"pages": sitemap_pages}, PUBLISH_DIR / "sitemap.xml")

    print(f"构建完成！共 {len(posts)} 篇文章 → {PUBLISH_DIR}")


if __name__ == "__main__":
    build()
