---
title: OpenList + STRM + rclone + Emby + 302 重定向网关（Deno）的家庭影院部署方案
created: 2026-01-16
updated: 2026-05-02
draft: false
---

> 环境：RHEL 10

> 本文方案同样适用其他 Linux 发行版，macOS 与 Windows 原理一致。

## 一、OpenList

> 添加网盘并为其生成 STRM 索引文件，暴露为 WebDav 以供挂载，同时提供 302 重定向直链。

1. **Docker 部署：**详情可见诸 [官方文档](https://doc.oplist.org/guide/installation/docker)，示例 `docker-compose.yml` 如下：

        services:
          openlist:
            image: 'openlistteam/openlist:latest'
            container_name: openlist
            user: '1000:1000'
            volumes:
              - './data:/opt/openlist/data'
            ports:
              - '5244:5244'
            environment:
              - UMASK=022
            restart: unless-stopped

2. **添加网盘：**

    以 115 网盘为例，路径：管理 → 存储 → 添加 → 115 网盘开放平台
  
    - 挂载路径：`/115`
    - WebDAV 策略：`302 重定向`
    - 限制速率：`1`
    - 访问令牌与刷新令牌：根据 [官方文档](https://doc.oplist.org/guide/drivers/115_open) 自行生成并填入
    - 其他保持默认
  
    ![openlist-strm-rclone-emby-302-100.png](https://pub-e4cebaa6c13f4b27a0ac28dc39ee18d0.r2.dev/openlist-strm-rclone-emby-302-100.png)
    
3. **生成 STRM 索引：**

    > STRM 是指向视频真实路径的文本文件。Emby 支持播放映射为 STRM 的视频资源，通过刮削 STRM 代替直接刮削网盘文件，可有效避免风控。
    
    OpenList 自带 STRM 文件生成功能，路径：OpenList → 管理 → 存储 → 添加 → STRM
    
    - 挂载路径：`/115_strm`
    - WebDAV 策略：`本机代理`
    - 路径：`/115`
    - 路径前缀：`/d`
    - 编码路径：`打开`
    - 携带签名：`打开`
    - 其他保持默认

    > 全局关闭签名时，可将「携带签名」选项设置为 `关闭`，路径：管理 → 设置 → 全局 → 关闭「签名所有」。

    ![openlist-strm-rclone-emby-302-200.png](https://pub-e4cebaa6c13f4b27a0ac28dc39ee18d0.r2.dev/openlist-strm-rclone-emby-302-200.png)

    > 示例 STRM 文件内容：`http://192.168.1.10:5244/d/115/TV%20SHOWS/%E7%8E%89.../Season%2001/S01E36.mp4?sign=xx7-biG1o...=:0`。

## 二、rclone

> 将 STRM 文件以 WebDAV 的形式挂载到本地，供 Emby 添加并刮削。

1. **安装与准备：**

    执行 `sudo dnf install rclone -y` 安装 `rclone`；

    执行 `sudo vim /etc/fuse.conf` 编辑配置文件，取消 `user_allow_other` 的注释。

2. **配置：**将 OpenList 的 WebDav 地址（e.g. `http://192.168.1.10:5244/dav`）新建为一个 Remote，本文方案中命名为 `openlist`；

3. **挂载：**将网盘视频资源对应的 STRM 文件挂载到本地。

        # 创建目录
        mkdir emby && cd emby
        mkdir {programdata,115_strm,tvshows,movies}
        
        # 挂载
        rclone mount openlist:/115_strm ./115_strm --vfs-cache-mode=full --allow-other --daemon

## 三、Emby

> 读取 STRM 文件，完成刮削与播放。

1. **Docker 部署：**示例 `docker-compose.yml` 文件如下：

        services:
          emby:
            image: emby/embyserver
            container_name: embyserver
            environment:
              - PUID=1000
              - PGID=1000
              - TZ=Asia/Shanghai
            volumes:
              - ./programdata:/config
              - ./tvshows:/data/tvshows
              - ./movies:/data/movies
              - ./115_strm:/mnt/115_strm
            ports:
              - 8096:8096
            devices:
              - /dev/dri:/dev/dri

2. **添加媒体库：**

    进入 Emby 后台设置，新增媒体库，文件夹路径：`/mnt/115_strm`。

    ![openlist-strm-rclone-emby-302-300.png](https://pub-e4cebaa6c13f4b27a0ac28dc39ee18d0.r2.dev/openlist-strm-rclone-emby-302-300.png)

## 四、302 重定向网关（Deno）

> Emby302Gateway：通过 Deno 运行，将 Emby STRM 播放请求重定向到 OpenList 返回的 CDN 直链地址。

1. **安装：**

    克隆 [Emby302Gateway](https://github.com/qvshuo/Emby302Gateway) 到本地：

        git clone https://github.com/qvshuo/Emby302Gateway.git --depth=1 && cd Emby302Gateway

    从 Deno 的 [Releases 页面](https://github.com/denoland/deno/releases) 直接下载单一可执行文件，或者：

        curl -fsSL https://deno.land/install.sh | sh

2. **配置：**

        cp .env.example .env

    编辑 `.env` 文件，根据实际情况填写：

        EMBY_HOST=http://localhost:8096         # Emby 地址
        EMBY_API_KEY=your_emby_api_key          # Emby API Key
        OPENLIST_ADDR=http://localhost:5244     # OpenList 地址
        OPENLIST_TOKEN=your_openlist_token      # OpenList 令牌，获取路径：管理 → 设置 → 其他 → 令牌
        PORT=18096                              # 网关端口，默认 18096
        CACHE_TTL=180                           # 缓存有效期，默认 3 分钟

3. **启动：**

        deno run --allow-net --allow-read=.env main.ts

    后台运行：

        nohup deno run --allow-net --allow-read=.env main.ts >> /tmp/emby302gateway.log 2>&1 &

## Emby 客户端

将 Emby 客户端的服务器地址配置为 Deno 网关地址：`http://你的服务器IP:18096`；
  
播放 STRM 视频时，实际请求将通过 302 重定向解析为 OpenList 返回的 CDN 直链，从而不再受 Emby 所在设备的网络带宽限制；本地视频及其他无法解析为 OpenList 直链的资源，仍由 Emby 按原方式处理。
