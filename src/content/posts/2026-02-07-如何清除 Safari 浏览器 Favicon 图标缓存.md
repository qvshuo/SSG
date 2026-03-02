---
title: 如何清除 Safari 浏览器 Favicon 图标缓存
created: 2026/02/07
draft: false
---

### 背景：

1. 在 macOS 上，Safari 浏览器存在一个理应是 BUG 的特性：

2. 当网站更新 Favicon 图标之后，Safari 在标签页中仍会显示缓存中的旧图标，即使刷新页面、重启浏览器，甚至清除网站数据，也无法解决此问题。

3. 这使得图标变更无法即时体现，给网页开发和调试带来不便。

### 解决步骤：

1. 关闭 Safari

    首先，确保完全退出 Safari 浏览器；

2. 清空 Favicon 缓存文件夹

    打开 访达，点击 前往 - 前往文件夹，进入以下路径：

        /Users/用户名/Library/Safari/Favicon Cache

    全选并将此文件夹内的全部内容移到废纸篓：

    ![clear-safari-favicon-cache-100.png](https://pub-e4cebaa6c13f4b27a0ac28dc39ee18d0.r2.dev/clear-safari-favicon-cache-100.png)

3. 清倒废纸篓

    清空缓存文件夹后，清倒废纸篓，以确保缓存被彻底移除。

4. 重新打开 Safari

    重新启动 Safari，刷新标签页，此时应显示正确的 Favicon 图标。
