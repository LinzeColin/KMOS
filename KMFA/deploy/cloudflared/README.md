# 上线段：Cloudflare Tunnel + Access（kmfa.linzezhang.com）

> 设计（任务包 09 第七节 + 修订 R5）：实例**零开放端口**（安全组只留 SSH），出网全走 Tunnel；
> 域名强制 Cloudflare Access 鉴权。App 容器仅监听 `127.0.0.1:8000`，`cloudflared` 以 host 网络直达回环。

## Owner 步骤（一次性，约 5 分钟，在 Cloudflare Zero Trust 面板）

1. **建 Tunnel**：Zero Trust → Networks → Tunnels → Create tunnel（连接器选 Docker）→ 复制 **token**。
2. **配公共主机名**：该 Tunnel → Public Hostname → `kmfa.linzezhang.com` → Service `http://127.0.0.1:8000`。
3. **上 Access 锁**：Zero Trust → Access → Applications → Add（Self-hosted，域名同上）→ 策略 Allow：你的邮箱（`linzezhang35@gmail.com`）一条即可。
4. 把 token 交给实例侧（agent 执行）：
   ```bash
   install -m 600 /dev/null /opt/kmfa/secrets/cloudflared.env
   echo "TUNNEL_TOKEN=<粘贴>" > /opt/kmfa/secrets/cloudflared.env
   cd /opt/kmfa/KMOS/KMFA/deploy/cloudflared && docker compose up -d
   ```

## 验收

- 面板 Tunnel 状态 HEALTHY；浏览器开 `https://kmfa.linzezhang.com` 先见 Access 登录页，登录后见 KMFA 仪表盘（`/ui/` 由 App 容器伺服）。
- 实例安全组核对：除 22 外无入站放行（Tunnel 是出站长连接，不需要入站口）。

## 纪律

- token 只进 `/opt/kmfa/secrets/`（600），**永不入仓**；换 token 只需重写 env 文件 + `docker compose restart`。
- 实例回收重建（R5 设计）：重跑本目录 `docker compose up -d` 即恢复——token 不变则域名自动回连。
