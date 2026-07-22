# 上线段：Cloudflare Tunnel + Access（kmfa.linzezhang.com）

> **注：此为 fallback 路径（无 Coolify 时）。** 云端主路径＝Coolify Traefik + Cloudflare 代理 DNS，见 `../coolify/README.md`；同一节点二选一，勿并用。
>
> 设计（任务包 09 第七节 + 修订 R5）：实例**零开放端口**（安全组只留 SSH），出网全走 Tunnel；
> 根域名公开，`/api*` 与 `/ops*` 由路径级 Cloudflare Access 加源站 JWT 校验保护。App 容器仅监听
> `127.0.0.1:8000`，`cloudflared` 以 host 网络直达回环。

## Owner 步骤（一次性，约 5 分钟，在 Cloudflare Zero Trust 面板）

1. **建 Tunnel**：Zero Trust → Networks → Tunnels → Create tunnel（连接器选 Docker）→ 复制 **token**。
2. **配公共主机名**：该 Tunnel → Public Hostname → `kmfa.linzezhang.com` → Service `http://127.0.0.1:8000`。
3. **上路径 Access 锁**：按主路径 `../coolify/README.md` 的 P2 第 8–10 步覆盖 `/api`、
   `/api/*`、`/ops`、`/ops/*`；host 级应用只对公共面 Bypass。生产 App compose 必须同时设置
   `KMFA_PRIVATE_OPS_REQUIRE_ACCESS=1`、team domain 与全部私有应用 Audience tags。
4. 把 Tunnel token 交给实例侧（agent 执行）：
   ```bash
   install -m 600 /dev/null /opt/kmfa/secrets/cloudflared.env
   echo "TUNNEL_TOKEN=<粘贴>" > /opt/kmfa/secrets/cloudflared.env
   cd /opt/kmfa/KMOS/KMFA/deploy/cloudflared && docker compose up -d
   ```

## 验收

- 面板 Tunnel 状态 HEALTHY；无 cookie 浏览器打开 `https://kmfa.linzezhang.com/` 直接见 KMFA；
  `/ui`、`/ui/` 单跳回 `/`；匿名私有路径不可达，已授权 Access 会话可达。
- 实例安全组核对：除 22 外无入站放行（Tunnel 是出站长连接，不需要入站口）。

## 纪律

- token 只进 `/opt/kmfa/secrets/`（600），**永不入仓**；换 token 只需重写 env 文件 + `docker compose restart`。
- 边缘异常先把 host 级 Application 恢复原 Owner Allow 策略，源站私有面守卫保持开启；不要用关闭守卫回滚。
- 实例回收重建（R5 设计）：重跑本目录 `docker compose up -d` 即恢复——token 不变则域名自动回连。
