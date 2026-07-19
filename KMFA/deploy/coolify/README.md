# KMFA 云端统一部署（Coolify）——主路径

> **治理原则（Owner 2026-07-18）**：统一治理、降复杂度、不加第四件。
> 只用已开的三件：**Coolify**（唯一部署/编排面板）+ **Cloudflare**（DNS/边缘 TLS）+ **OVH VPS**（主机）。
> 本目录即云端主路径；`../skills-runtime/bootstrap.sh` 与 `../cloudflared/` 为**无 Coolify 时的 fallback 裸机路径**，非主路径。

节点：OVH Singapore VPS-1，amd64，Ubuntu 24.04，2 vCore/3.7GB/40GB。部署链已 #109 在 amd64 端到端出证。

---

## 前置（operate 线拍板 2026-07-18；Coolify 资源类型 = Docker-Compose 指向本仓）

- ✅ **Docker 已就绪**（29.6.2 + compose + buildx，amd64）。
- ⏳ **Owner 一次点连 Coolify 的 GitHub App**（STAGE-06.3）——连好后由 operate 线在 Coolify 建 project + 连 GitHub 源、登记本 `docker-compose.yml` 为 Docker-Compose 资源。分工：我维护仓内部署件（真相源），operate 线在 Coolify 登记指向它。
- ⏳ **容量 Gate**（operate 线做）：Coolify+PG+Redis 常驻 ~1.3G，主机 3.7G + 2G swap，资金周报 OCR 峰值 ~1G 需错峰确认。过闸后 operate 线发 **"P1-GO"** 方动主机——在此之前只改仓、不碰主机。

## P1 —— 起 skills 栈（dry-run，不投递）

1. **Coolify → New Resource → Docker Compose**，Git 源指向本仓，Compose 路径填：
   `KMFA/deploy/coolify/docker-compose.yml`
   （默认只含 `skills` 服务；`app` 在 `full` profile 后置，P1 不起。）
2. **Environment Variables**（Coolify 面板设，键位见同目录 `.env.example`）：
   - `KMFA_DELIVERY_ENABLED=0`（务必 0——双跑期只记日志不投递）。
   - 敏感项（`DINGTALK_ROBOT_URL/SIGNING_KEY`、`DINGTALK_DING_ROBOT_CODE`、`KMFA_ALERT_WEBHOOK_TOKEN`）**勾 "Is Secret"**（Coolify 以 APP_KEY 加密；compose 内只有 `${KEY}` 占位、值不入仓）。键名以代码实读为准（勿把 `KMFA_ALERT_WEBHOOK_TOKEN` 简写）。有值填、暂无可留空（缺值告警空跑，不阻塞起容器）。
   - dws 登录态**不是 env**：由托管 named volume `kmfa-dws-auth` 持久，Owner 首启 `dws auth login --device` 写一次即可。
3. **Deploy**。起来后 Coolify 里 `kmfa-skills` 应为 healthy（cron 存活 + 台账）。
   - 自检：Coolify → skills → Terminal → `/opt/runtime/run_skill.sh self-audit` → 应 rc=0（证据链/血缘/双平面全绿）。
   - 时区自证：Terminal → `date +%z` 应为 `+0800`（entrypoint 守卫已挡任何非北京时区启动）。

## 👤 只有 Owner 本人能做的两步（其余全自动）

> 这两步基建线和我都替不了。

1. **dws 设备码登录**（钉钉手机点一次）：Coolify → skills → Terminal：
   ```
   dws auth login --device                 # 手机弹确认 → 点同意
   dws pat browser-policy --enabled=false --format json --yes
   ```
   登录后在 Coolify 把 `KMFA_DINGTALK_ATTENDANCE_ALLOW_DWS_COMMANDS=1` 并重部署。
2. **Codex 应用停用 6 条旧排程**（6 次点击）：`kmfa / kmfa-3 / kmfa-4 / kmfa-5 / kmfa-dws / dws-auth-keepalive-2`——工作目录已删、每天空跑失败，直接停用，云端一刀接管。停完告我，我把契约 toml 同步 DISABLED。

## P1 验收 —— 测试发送 + 双跑

3. **测试发送**（Owner 授权对象＝张霖泽）：Terminal：
   ```
   /opt/runtime/test_send.sh 张霖泽                    # 默认 dry-run，只解析+打印
   KMFA_TEST_SEND_CONFIRM=1 /opt/runtime/test_send.sh 张霖泽   # 确认后真发一条
   ```
4. **dry-run 双跑 ≥3 天**（`KMFA_DELIVERY_ENABLED=0`，云端北京锚与旧排程并行、只比对产物）。
5. 无异常 → Coolify 置 `KMFA_DELIVERY_ENABLED=1` 重部署 → 正式投递。

## P2 —— 起 App 栈（容量确认后）

6. 观测 P1 内存无碍后，在 Coolify 为本资源**启用 `full` profile**（Compose profiles → 勾 `full`）或设 `COMPOSE_PROFILES=full`，重部署 → `kmfa-app` 起。
7. **域名**：Coolify 给 `app` 服务设 `kmfa.linzezhang.com`（Coolify Traefik 自动签发/路由）；**Cloudflare** 加一条**代理（橙云）** A 记录 `kmfa` → OVH 公网 IP（或按 Coolify 提示的 CNAME）。App 仅经 Traefik 暴露，主机不额外开放端口。

---

## 容量提示（3.7GB）

- skills：idle 数百 MB；资金周报 OCR（onnxruntime PP-OCRv4）瞬时峰值 ~1GB、cron 每日数次非常驻。
- app：~150–200MB。
- Coolify 自身 + 其 PG/Redis 常驻约 1–1.5GB——故 P1 先只起 skills、观测后再上 app。

## 与 fallback 裸机路径的关系

无 Coolify 时可用 `../skills-runtime/bootstrap.sh`（curl|bash 装 docker + compose up）+ `../cloudflared/`（Cloudflare Tunnel）。两者与本 Coolify 路径**互斥**：同一节点只用其一，避免平行未治理轨道。主路径＝Coolify。
