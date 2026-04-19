---
title: 让 Quantumult X 变相支持 NaïveProxy 协议的实现方案
created: 2026-04-19
draft: false
---

> 思路：在设备本地或局域网运行 naive 客户端监听 SOCKS5，再由 Quantumult X 接入该 SOCKS5 代理，变相实现 NaïveProxy 协议支持。

## 一、前期准备

- 一个可用域名
- 一台公网 VPS
- 为域名添加一条 `A` 记录，指向 VPS 的公网 IP

## 二、部署服务端

服务端需运行集成 `forwardproxy@naive` 插件的 Caddy。

### A. 获取服务端程序

**方式一：使用 xcaddy 自行编译**

参考 [官方文档](https://github.com/klzgrad/naiveproxy#server-setup) 执行：

```bash
go install github.com/caddyserver/xcaddy/cmd/xcaddy@latest
~/go/bin/xcaddy build --with github.com/caddyserver/forwardproxy=github.com/klzgrad/forwardproxy@naive
```

**方式二：复用官方包并替换二进制文件**

为便于通过 systemd 管理，可先安装发行版官方 Caddy，再利用 override 机制替换其可执行文件。以 AlmaLinux 为例：

#### 安装官方包

```bash
sudo dnf install dnf-plugins-core -y
sudo dnf copr enable @caddy/caddy -y
sudo dnf install caddy -y
```

#### 下载并保存插件版 Caddy

```bash
curl -L -o caddy-forwardproxy-naive.tar.xz \
  https://github.com/klzgrad/forwardproxy/releases/download/v2.10.0-naive/caddy-forwardproxy-naive.tar.xz
tar -xf caddy-forwardproxy-naive.tar.xz
sudo mv caddy-forwardproxy-naive/caddy /usr/local/bin/naive
sudo chown root:root /usr/local/bin/naive
sudo chmod 755 /usr/local/bin/naive
```

#### 替换 caddy 二进制文件

```bash
sudo systemctl edit caddy
```

输入以下内容：

```
[Service]
ExecStart=
ExecStart=/usr/local/bin/naive run --environ --config /etc/caddy/Caddyfile

ExecReload=
ExecReload=/usr/local/bin/naive reload --config /etc/caddy/Caddyfile --force
```

### B. 编辑 Caddyfile

编辑 `/etc/caddy/Caddyfile`，参考配置：

```caddy
{
    order forward_proxy before file_server
}
:443, example.com {
    tls me@example.com
    forward_proxy {
        basic_auth user pass
        hide_ip
        hide_via
        probe_resistance
    }
    file_server {
        root /var/www/html
    }
}
```

- `example.com`：你的域名
- `me@example.com`：用于申请 ACME 证书的邮箱
- `basic_auth user pass`：认证凭据，需与客户端保持一致

> 提示：只需在 `/var/www/html` 目录下放置一个 `index.html` 文件，即可使该域名指向一个普通的网站页面以实现良好伪装。

### C. 重载并启动服务

```bash
sudo systemctl daemon-reload
sudo systemctl restart caddy
```

## 三、配置客户端

1. 从 NaïveProxy [发布页](https://github.com/klzgrad/naiveproxy/releases/latest) 下载对应平台的客户端压缩包；

2. 解压出 `naive` 可执行文件，并赋予执行权限（`chmod +x naive`）；

3. 创建配置文件 `config.json`：

        {
          "listen": "socks://0.0.0.0:1080",
          "proxy": "https://user:pass@example.com"
        }

4. 启动客户端：

        ./naive /path/to/config.json
        # 或直接通过命令行参数启动
        ./naive --listen socks://0.0.0.0:1080 --proxy https://user:pass@example.com

启动后，客户端将在本机 `0.0.0.0:1080` 监听 SOCKS5 代理，并通过 NaïveProxy 协议将流量转发至 VPS。

> 提示：建议运行客户端的设备配置静态 IP，以防局域网内其他设备因 IP 变动无法连接代理。

## 五、接入 Quantumult X

1. 打开 Quantumult X 配置文件，在 `[server_local]` 添加：

         socks5 = 192.168.1.100:1080, fast-open=false, udp-relay=false, tag=naiveproxy
         ;此处的 `192.168.1.100` 应替换为实际运行 naive 客户端的 IP地址。

2. 在 `[filter_local]` 添加直连规则，防止代理流量回环：

         host-suffix, example.com, direct

3. 保存配置文件，Quantumult X 将自动重载。选中新增的 `naiveproxy` 节点后，访问受限网站的流量路径如下：`Quantumult X → 本机 naive (SOCKS5) → VPS (naiveproxy) → 目标站点`。

## 六、结语

   至此，即可通过本地转发实现 Quantumult X 对 NaïveProxy 协议的支持。
