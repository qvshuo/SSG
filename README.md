# 静态博客生成器

使用 Python + Jinja2 + Markdown，生成纯静态 HTML 博客。

## 快速开始

```bash
# 安装依赖
pip install -r requirements.txt

# 配置（编辑 ssg.py 顶部的 CONFIG）
CONFIG = {"author": "你的名字", "url": "https://your-domain.com"}

# 写文章（src/content/posts/*.md）
---
title: 我的第一篇文章
created: 2026-01-24
updated: 2026-02-28
draft: false
---
正文...

# 构建
python ssg.py

# 本地预览
cd publish && python -m http.server 8000
```

## 目录结构

```
ssg.py              # 主程序（含配置）
src/
├── layouts/        # Jinja2 模板
│   ├── base.html     # 基础模板
│   ├── index.html    # 首页模板
│   ├── article.html  # 文章模板
│   └── sitemap.xml   # Sitemap 模板
├── styles/
│   └── styles.css    # 样式
├── fonts/           # 字体文件（Inter、Source Serif 4、Source Han Serif、Google Sans Code）
├── content/
│   ├── posts/        # 文章 Markdown 文件
│   └── about.md      # 关于页
└── images/           # 图片资源
publish/             # 输出目录
```

## 特性

- 响应式布局，最大宽度 720px
- 明暗主题自动切换（基于 `prefers-color-scheme`）
- 文章 URL 使用文件名（可读性强）
- 毛玻璃效果 Header
- 代码块样式
- HTML 压缩输出
- Sitemap 自动生成

## Frontmatter 字段

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| title | string | 是 | 文章标题 |
| created | string | 是 | 创建日期，格式 YYYY-MM-DD |
| updated | string | 否 | 更新日期，格式 YYYY-MM-DD |
| draft | boolean | 否 | 设为 true 则不发布 |

---

# 供 AI 阅读的技术文档

## 技术栈

- Python 3 + Jinja2 + Markdown
- 纯 CSS，无框架

## 核心依赖

```
jinja2
markdown
minify_html
```

或使用：

```bash
pip install -r requirements.txt
```

## 站点配置

直接修改 `ssg.py` 顶部的 `CONFIG` 字典：

```python
CONFIG = {"author": "你的名字", "url": "https://your-domain.com"}
```

## 模板继承

```
base.html
    ├── index.html    # 首页，使用 block content
    └── article.html  # 文章页，使用 block content
```

### Jinja2 Blocks

- `{% block title %}` - 页面标题
- `{% block content %}` - 主要内容
- `{% block links %}` - Header 右侧链接

## Header 布局

- `position: sticky` 固定顶部
- `backdrop-filter: blur(10px)` 毛玻璃效果
- 左侧：站点标题（链接到首页）
- 右侧：首页 About，文章页 Articles + About

## 构建流程

1. 读取 ssg.py 顶部的 CONFIG
2. 清空 publish 目录（保留目录本身）
3. 复制 CSS、图片、字体（含子目录）
4. 解析 posts/*.md（过滤草稿，按 created 倒序）
5. 渲染 Jinja2 模板
6. 压缩 HTML 输出（使用 minify_html）
7. 生成 sitemap.xml
8. 输出 index.html、about.html、posts/*.html

## 页面路由

| 页面 | URL |
|------|-----|
| 首页 | /index.html |
| 文章 | /posts/{文件名}.html |
| 关于 | /about.html |

## 样式 (styles.css)

### 布局

- 最大宽度：720px (45rem)
- 基础字号：16px (1rem)
- 正文字号：1rem (16px)
- 行高：1.625
- REM 单位：基于 16px

### CSS 变量

| 变量 | 说明 | 浅色默认值 | 深色默认值 |
|------|------|-----------|-----------|
| --page-background | 页面背景颜色 | #ffffff | #212121 |
| --text-primary | 主文字颜色 | #212326 | #f5f5f5 |
| --text-secondary | 次要文字颜色 | #4d4f51 | #c4c4c4 |
| --text-muted | 弱化文字颜色 | #909193 | #7b7b7b |
| --header-background | Header 背景色 | rgba(255,255,255,.9) | rgba(33,33,33,.9) |
| --header-border | Header 边框色 | rgba(229,231,235,.5) | rgba(26,24,20,.5) |
| --header-shadow | Header 阴影色 | rgba(31,34,37,.03) | rgba(224,221,218,.07) |
| --hr-background | 分割线颜色 | rgba(228,228,229,.5) | rgba(228,228,229,.07) |
| --code-color | 代码文字颜色 | #3d3d3d | #e5e5e5 |
| --code-background | 代码背景颜色 | #fbfbfb | #2a2a2a |
| --code-border | 代码边框颜色 | #e9e9e9 | #424242 |
| --link-color | 链接颜色 | #0f5491 | #91defa |
| --font-serif | 衬线字体 | "Source Han Serif", "Source Serif 4", serif | 同左 |
| --font-mono | 等宽字体 | 'Google Sans Code', ui-monospace, monospace | 同左 |

### 标题样式

| 元素 | 字号 | 字重 | 上下间距 |
|------|------|------|---------|
| h1 | 2rem | 700 | 3rem / .75rem |
| h2 | 1.375rem | 700 | 2.25rem / .625rem |
| h3 | 1.2rem | 600 | 1.85rem / .5rem |
| h4-h6 | 1.05rem | 500 | 1.5rem / .5rem |

### 字体定义

- **Inter** (可变字体 100-900)：无衬线正文字体
- **Source Serif 4** (可变字体 200-900)：衬线字体
- **Source Han Serif** (可变字体 100-900)：思源宋体，中文衬线字体
- **Google Sans Code** (可变字体 100-900)：等宽字体，用于代码

### 排版细节

- 链接颜色使用 CSS 变量 `--link-color`，深色模式下自动切换为浅蓝色
- 图片/iframe 圆角：.25rem (4px)
- 代码块圆角：.25rem (4px)，带轻微阴影

## 可用变量

- `config.author` - 作者名称
- `config.url` - 站点 URL
- `posts` - 文章列表（按 created 倒序）
- `post` - 当前文章对象（含 title、created、updated、content）

## 注意事项

1. 草稿设置 `draft: true` 不会被构建
2. 图片路径相对于 Markdown 文件所在目录
3. 日期格式使用 `YYYY-MM-DD`
4. 避免文件名相同的文章
