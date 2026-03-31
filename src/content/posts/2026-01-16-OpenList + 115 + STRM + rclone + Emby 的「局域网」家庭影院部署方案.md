---
title: OpenList + 115 + STRM + rclone + Emby 的「局域网」家庭影院部署方案
created: 2026-01-16
updated: 2026-04-01
draft: false
---

> 适用人群：

> 1. 只在局域网内观看视频，没有公网访问的需求；
> 2. 倾向选择积极维护且被广泛使用的软件；
> 3. 以尽量少的软件达成目标，降低配置复杂度与维护成本。

> 环境：RHEL 10

> 本文方案同样适用其他 Linux 发行版，macOS/Windows 下的实现原理亦基本一致。

### 一、OpenList

> OpenList 负责将 115 网盘转换为 WebDav 并生成 STRM 索引文件。

1. 使用 Docker 部署 OpenList，详情可见 [官方文档](https://doc.oplist.org/guide/installation/docker)，本文方案的 `docker-compose.yml` 内容如下：

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

2. **关闭签名：**仅针对局域网个人使用的场景，部署完成后：OpenList - 管理 - 设置 - 全局 - 关闭「签名所有」
3. **添加 115 网盘：**OpenList - 管理 - 存储 - 添加 - 115 网盘开放平台，详情参考 [官方文档的说明](https://doc.oplist.org/guide/drivers/115_open)：
    - 挂载路径： `/115`
    - WebDAV 策略：302 重定向（OpenList 只负责为后续步骤的 rclone 提供视频资源的 CDN 地址，其本身不代理流量）
    - 限制速率：1（限制并发线程，规避网盘风控）
    - 其他保持默认

        ![openlist-115-strm-rclone-emby-100.png](https://pub-e4cebaa6c13f4b27a0ac28dc39ee18d0.r2.dev/openlist-115-strm-rclone-emby-100.png)
    
        ![openlist-115-strm-rclone-emby-200.png](https://pub-e4cebaa6c13f4b27a0ac28dc39ee18d0.r2.dev/openlist-115-strm-rclone-emby-200.png)
    
4. **生成 STRM 索引**：

    > STRM 文件本质是一个文本文件，指向视频资源的真实路径，Emby 可播放 STRM 指向的目标内容；通过将网盘资源映射为 STRM 文件，可以通过刮削 STRM 来代替直接刮削网盘文件，从而避免风控；

    OpenList 自带了 STRM 文件生成功能，故无需额外使用其他软件，直接：OpenList - 管理 - 存储 - 添加 - STRM：
    
    - 挂载路径：`/115_strm`
    - 路径：`/115` （即上述 115 网盘的挂载路径）
    - 站点 URL：`/mnt` （文末补充如此配置的缘由）
    - **路径前缀：空**
    - **编码路径：关**（本文方案中，开启会导致 Emby 只能播放纯英文路径的视频）
    - 其他保持默认

        ![openlist-115-strm-rclone-emby-300.png](https://pub-e4cebaa6c13f4b27a0ac28dc39ee18d0.r2.dev/openlist-115-strm-rclone-emby-300.png)
        
        ![openlist-115-strm-rclone-emby-400.png](https://pub-e4cebaa6c13f4b27a0ac28dc39ee18d0.r2.dev/openlist-115-strm-rclone-emby-400.png)

    - 示例 STRM 文件内容：
    
        `/mnt/115/TV Shows/玉茗茶骨 (2025) [tmdbid=284512]/Season 01/S01E02.mp4`

### 二、rclone

> rclone 负责将 115 网盘资源和 STRM 文件以 WebDAV 的形式挂载到本地。

1. **安装与环境准备**：以 RHEL 10 Linux 为例，其他系统请善用搜索引擎检索互联网上的教程。
    - 执行 `sudo dnf install rclone -y` 安装 rclone；
    - 执行 `sudo vim /etc/fuse.conf` 编辑配置文件，取消 `user_allow_other` 的注释。
2. **配置：**将 OpenList 暴露的 WebDav（e.g. `http://192.168.1.100:5244/dav`）新建为一个 Remote，本文方案中命名为 openlsit，过程不再赘述，依旧请善用搜索引擎；
3. **挂载：**将 115 网盘和视频资源对应的 STRM 文件挂载到本地。

        # 创建 Emby 所需目录
        mkdir emby && cd emby
        mkdir {programdata,115,115_strm,tvshows,movies}
        
        # 执行挂载
        rclone mount openlist:/115 ./115 --vfs-cache-mode=full --allow-other --daemon
        rclone mount openlist:/115_strm ./115_strm --vfs-cache-mode=full --allow-other --daemon

### 三、Emby

1. **部署：**使用 Docker 部署 Emby，并将 rclone 挂载好的宿主机目录映射进容器，本文方案的 `docker-compose.yml` 内容如下：

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
            - ./115:/mnt/115
            - ./115_strm:/mnt/115_strm
            ports:
            - 8096:8096
            devices:
            - /dev/dri:/dev/dri
            extra_hosts:
            - "host.docker.internal:host-gateway"

2. **初始化媒体库：**
    - 进入 Emby 后台设置，添加媒体库；
    - 媒体库路径：`/mnt/115_strm`，不要选择 `/mnt/115`，否则会因刮削而被风控。

        ![openlist-115-strm-rclone-emby-500.png](https://pub-e4cebaa6c13f4b27a0ac28dc39ee18d0.r2.dev/openlist-115-strm-rclone-emby-500.png)

### 四、补充

通过设置 OpenList 中 STRM 存储的站点 URL 为 Emby 容器内的 `/mnt`，确保 STRM 实际指向映射进 Emby 容器的由 rclone 本地挂载的 115 网盘资源，如此：

- rclone 可自动跟随 OpenList 返回的 302 重定向 CDN 地址，并通过本地 VFS 机制承接视频数据的读取与缓存，相比 STRM 直接指向 OpenList 的文件地址，启播速度和拖动进度的响应明显更快；
- 此外，Emby 不支持自动跟随 302 重定向。STRM 直接指向 OpenList 的文件地址，还会导致除 Emby 网页端之外的第三方客户端（e.g. Infuse）视频启播失败。
