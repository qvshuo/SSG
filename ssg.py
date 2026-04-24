"""静态博客生成器"""

import re
import shutil
import sys
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, List, Tuple
from urllib.parse import unquote, urlsplit, urlunsplit

import markdown
import minify_html
from jinja2 import Environment, FileSystemLoader, select_autoescape

CONFIG: Dict[str, str] = {"author": "安静", "url": "https://anjing.art"}
DEFAULT_PREVIEW_PORT = 38427

BASE_DIR = Path(__file__).parent
SRC_DIR = BASE_DIR / "src"
CONTENT_DIR = SRC_DIR / "content"
POSTS_DIR = CONTENT_DIR / "posts"
PUBLISH_DIR = BASE_DIR / "publish"
CONTENT_ASSETS_DIR = PUBLISH_DIR / "_content"

# Jinja2 模板环境
jinja_env = Environment(
    loader=FileSystemLoader(SRC_DIR / "layouts"),
    autoescape=select_autoescape(["html", "xml"]),
    trim_blocks=True,
    lstrip_blocks=True,
)

FRONTMATTER_RE = re.compile(r"^---\s*\r?\n(.*?)\r?\n---\s*(?:\r?\n|$)", re.DOTALL)
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
HTML_TAG_RE = re.compile(r"<!--|</?[A-Za-z][A-Za-z0-9-]*\b[^>]*>", re.DOTALL)
FENCED_CODE_RE = re.compile(r"(^|\n)(```.*?```|~~~.*?~~~)", re.DOTALL)
INLINE_CODE_RE = re.compile(r"`[^`]*`")
AUTO_LINK_RE = re.compile(r"<(?:https?://|mailto:)[^>\s]+>")
ATTR_RE = re.compile(r'(?P<attr>\b(?:href|src))=(?P<quote>["\'])(?P<value>.*?)(?P=quote)')


def fail(message: str) -> None:
    """打印错误并退出。"""
    print(f"错误：{message}", file=sys.stderr)
    sys.exit(1)


def read_text(filepath: Path) -> str:
    """读取 UTF-8 文本，并兼容 BOM。"""
    try:
        return filepath.read_text(encoding="utf-8").lstrip("\ufeff")
    except FileNotFoundError:
        fail(f"文件不存在 - {filepath}")
    except UnicodeDecodeError as exc:
        fail(f"文件编码错误 - {filepath}: {exc}")


def parse_frontmatter(text: str) -> Tuple[Dict[str, str], str]:
    """解析 frontmatter（仅支持单行 key: value 格式）。"""
    match = FRONTMATTER_RE.match(text)
    if not match:
        return {}, text

    meta = {}
    for line in match.group(1).splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            meta[key.strip()] = value.strip()
    return meta, text[match.end() :]


def normalize_date(value: str) -> str:
    """统一日期分隔符为 '-'。"""
    return value.strip().replace("/", "-")


def validate_date(value: str, field_name: str, filepath: Path, *, required: bool) -> str:
    """校验日期格式。"""
    normalized = normalize_date(value)
    if not normalized:
        if required:
            fail(f"{filepath} 缺少必填字段 {field_name}")
        return ""
    if not DATE_RE.fullmatch(normalized):
        fail(f"{filepath} 的 {field_name} 日期格式无效：{value}")
    return normalized


def validate_draft(value: str, filepath: Path) -> bool:
    """校验 draft 字段。"""
    normalized = value.strip().lower()
    if normalized in {"", "false"}:
        return False
    if normalized == "true":
        return True
    fail(f"{filepath} 的 draft 只能是 true 或 false")


def reject_raw_html(body: str, filepath: Path) -> None:
    """拒绝 Markdown 中的原始 HTML，避免意外脚本注入。"""
    stripped = FENCED_CODE_RE.sub("", body)
    stripped = INLINE_CODE_RE.sub("", stripped)
    stripped = AUTO_LINK_RE.sub("", stripped)
    if HTML_TAG_RE.search(stripped):
        fail(f"{filepath} 包含原始 HTML，请改用 Markdown 语法")


def post_url(filepath: Path) -> str:
    """用文件名（不含扩展名）作为 URL slug。"""
    return filepath.stem + ".html"


def markdown_url(filepath: Path) -> str:
    """把内容文件路径映射为站内 URL。"""
    if filepath == CONTENT_DIR / "about.md":
        return "/about.html"
    if filepath.parent == POSTS_DIR:
        return f"/posts/{post_url(filepath)}"
    if filepath.parent == CONTENT_DIR:
        return f"/{filepath.stem}.html"
    fail(f"不支持的 Markdown 链接目标 - {filepath}")


def is_special_url(value: str) -> bool:
    """判断是否应跳过改写。"""
    return value.startswith(("/", "#", "mailto:", "tel:")) or "://" in value


def resolve_local_path(source_path: Path, relative_path: str) -> Path:
    """把相对路径解析到仓库内实际文件。"""
    target = (source_path.parent / unquote(relative_path)).resolve()
    if not target.is_file():
        fail(f"{source_path} 引用了不存在的本地文件 - {relative_path}")
    if not target.is_relative_to(CONTENT_DIR):
        fail(f"{source_path} 引用了 content 目录之外的文件 - {relative_path}")
    return target


def copy_content_asset(asset_path: Path) -> str:
    """复制内容资源到输出目录，并返回站内绝对路径。"""
    relative_path = asset_path.relative_to(CONTENT_DIR)
    output_path = CONTENT_ASSETS_DIR / relative_path
    output_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(asset_path, output_path)
    return f"/_content/{relative_path.as_posix()}"


def rewrite_html_paths(html_text: str, source_path: Path) -> str:
    """把文章内容中的本地相对路径改写为站内可访问路径。"""

    def replace(match: re.Match[str]) -> str:
        attr = match.group("attr")
        quote = match.group("quote")
        value = match.group("value")

        if not value or is_special_url(value):
            return match.group(0)

        parts = urlsplit(value)
        if not parts.path:
            return match.group(0)

        target = resolve_local_path(source_path, parts.path)
        if attr == "href" and target.suffix.lower() == ".md":
            rewritten_path = markdown_url(target)
        else:
            rewritten_path = copy_content_asset(target)

        rewritten = urlunsplit(("", "", rewritten_path, parts.query, parts.fragment))
        return f"{attr}={quote}{rewritten}{quote}"

    return ATTR_RE.sub(replace, html_text)


def parse_markdown(filepath: Path) -> Dict[str, Any]:
    """解析 Markdown 文件，返回页面字典。"""
    text = read_text(filepath)
    meta, body = parse_frontmatter(text)

    title = meta.get("title", "").strip()
    if not title:
        fail(f"{filepath} 缺少必填字段 title")

    created = validate_date(meta.get("created", ""), "created", filepath, required=True)
    updated = validate_date(meta.get("updated", ""), "updated", filepath, required=False)
    draft = validate_draft(meta.get("draft", "false"), filepath)

    reject_raw_html(body, filepath)

    html = markdown.Markdown(extensions=["extra"]).convert(body)
    html = rewrite_html_paths(html, filepath)

    return {
        "title": title,
        "created": created,
        "updated": updated,
        "draft": draft,
        "content": html,
    }


def render_to_file(
    template_name: str, context: Dict[str, Any], output_path: Path
) -> None:
    """渲染模板并写入文件。"""
    try:
        html = jinja_env.get_template(template_name).render(context)
        if output_path.suffix.lower() == ".html":
            html = minify_html.minify(html)
        output_path.write_text(html, encoding="utf-8")
    except Exception as exc:
        fail(f"渲染模板失败 - {template_name}: {exc}")


def clean_output_dir(path: Path) -> None:
    """清空输出目录（保留目录本身）。"""
    if not path.exists():
        path.mkdir(parents=True)
        return

    for item in path.iterdir():
        if item.is_file():
            item.unlink()
        elif item.is_dir():
            shutil.rmtree(item)


def copy_resources(src: Path, dest: Path, dirs: List[str]) -> None:
    """复制静态资源目录（含子目录）。"""
    for name in dirs:
        src_dir = src / name
        if src_dir.exists():
            shutil.copytree(src_dir, dest / name, dirs_exist_ok=True)


def build_sitemap(
    base_url: str, posts: List[Dict[str, Any]], standalone_pages: List[Dict[str, Any]]
) -> List[Dict[str, str]]:
    """构建 Sitemap 数据。"""
    pages = []

    latest = posts[0] if posts else None
    index_lastmod = (latest["updated"] or latest["created"]) if latest else ""
    pages.append({"loc": f"{base_url}/", "lastmod": index_lastmod})

    for post in posts:
        pages.append(
            {
                "loc": f"{base_url}/posts/{post['url']}",
                "lastmod": (post["updated"] or post["created"]),
            }
        )

    for page in standalone_pages:
        pages.append(
            {
                "loc": f"{base_url}/{page['url']}",
                "lastmod": (page["updated"] or page["created"]),
            }
        )

    return pages


def build() -> None:
    """构建静态博客。"""
    if not POSTS_DIR.exists():
        fail(f"文章目录不存在 - {POSTS_DIR}")

    clean_output_dir(PUBLISH_DIR)

    copy_resources(SRC_DIR, PUBLISH_DIR, ["styles", "images", "fonts"])
    (PUBLISH_DIR / "posts").mkdir(parents=True, exist_ok=True)

    posts: List[Dict[str, Any]] = []
    md_files = list(POSTS_DIR.glob("*.md"))
    if not md_files:
        print("警告：未找到任何文章")

    for md_file in md_files:
        post = parse_markdown(md_file)
        if not post["draft"]:
            post["url"] = post_url(md_file)
            posts.append(post)

    posts.sort(key=lambda post: post["created"], reverse=True)

    render_to_file("index.html", {"config": CONFIG, "posts": posts}, PUBLISH_DIR / "index.html")

    for post in posts:
        render_to_file(
            "article.html",
            {"config": CONFIG, "post": post},
            PUBLISH_DIR / "posts" / post["url"],
        )

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

    base_url = CONFIG["url"].rstrip("/")
    sitemap_pages = build_sitemap(base_url, posts, standalone_pages)
    render_to_file("sitemap.xml", {"pages": sitemap_pages}, PUBLISH_DIR / "sitemap.xml")

    print(f"构建完成！共 {len(posts)} 篇文章 → {PUBLISH_DIR}")


def serve(port: int = DEFAULT_PREVIEW_PORT) -> None:
    """构建后启动本地预览服务。"""
    build()
    handler = partial(SimpleHTTPRequestHandler, directory=str(PUBLISH_DIR))
    server = ThreadingHTTPServer(("localhost", port), handler)
    print(f"本地预览：http://localhost:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n已停止预览服务。")
    finally:
        server.server_close()


def main() -> None:
    """命令行入口。"""
    if len(sys.argv) == 1:
        build()
        return

    if sys.argv[1] == "serve":
        if len(sys.argv) > 3:
            fail("用法：python3 ssg.py [serve [port]]")
        try:
            port = DEFAULT_PREVIEW_PORT if len(sys.argv) == 2 else int(sys.argv[2])
        except ValueError:
            fail("端口必须是整数")
        serve(port)
        return

    fail("用法：python3 ssg.py [serve [port]]")


if __name__ == "__main__":
    main()
