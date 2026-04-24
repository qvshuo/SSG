# 静态博客生成器

## 快速开始

```bash
# 安装依赖
pip install -r requirements.txt

# 构建站点
python3 ssg.py

# 本地预览
python3 ssg.py serve
```

本地预览支持手动指定端口，例如 `python3 ssg.py serve 9000`。

## 内容结构

```text
src/
├── content/
│   ├── posts/      # 博客文章
│   └── about.md    # 关于页
├── layouts/        # 页面模板
├── styles/         # 样式
├── images/         # 站点静态图片
└── fonts/          # 字体文件
```

构建完成后，生成结果位于 `publish/`。

## 写文章

文章存放在 `src/content/posts/` 下，文件名会直接成为页面 URL，建议使用：

```text
YYYY-MM-DD-title.md
```

每篇文章都需要 frontmatter：

```md
---
title: 我的第一篇文章
created: 2026-04-25
updated: 2026-04-26
draft: false
---
```

规则：

- `title` 和 `created` 必填。
- 日期格式必须是 `YYYY-MM-DD`。
- `draft: true` 的文章不会被发布。
- 本地图片和附件可以使用相对路径，构建时会自动复制。
- 站内 Markdown 链接会自动改写为对应的 `.html` 页面。
- Markdown 中不支持原始 HTML。

## 站点配置

直接修改 `ssg.py` 顶部的 `CONFIG`：

```python
CONFIG = {"author": "你的名字", "url": "https://your-domain.com"}
```
