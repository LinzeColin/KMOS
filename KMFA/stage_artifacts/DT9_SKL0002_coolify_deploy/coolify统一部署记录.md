# KMFA 云端统一部署（Coolify）开发与本地实证记录（2026-07-18）

## 治理决策（Owner 2026-07-18）
"一定要统一治理、降低治理难度复杂度、不加第四件"——现有 **Cloudflare + Coolify + OVH** 三件够用。据此定案：**Coolify = 唯一部署/编排面板，Cloudflare = DNS/边缘 TLS，OVH = 主机**；弃用独立 `bootstrap.sh` + `cloudflared` Tunnel 作主路径（降为 fallback），不搞平行未治理轨道。本机 docker 仅临时开发用，长期稳定运行/上线一律云端。

## 交付件（`KMFA/deploy/coolify/`）
- `docker-compose.yml`：单一 compose 管两栈——`skills`（默认起）+ `app`（藏 `full` profile，P2 容量确认后再起）。复用 #109 已端到端出证的 `../skills-runtime/Dockerfile`（零重打包）；技能代码经**相对绑定挂载** `../../..`（=仓根，Coolify checkout）只读进容器；env/secrets 从 Coolify 面板注入（`${VAR:-default}` 优雅缺省）；`TZ=Asia/Shanghai`（entrypoint `+0800` 守卫兜底）；app 经 Coolify Traefik 暴露、域名面板设 `kmfa.linzezhang.com`。
- `.env.example`：Coolify 环境键位（投递开关/考勤闸/钉钉渠道/告警 webhook）。
- `README.md`：Coolify 登记 → P1 skills(dry-run) → Owner 两步（dws 设备码 + 停 6 排程）→ 测试发张霖泽 → 双跑 → P2 app + Cloudflare 代理 DNS。3.7GB 容量分批。

## 本地实证（vanilla `docker compose`，approximates Coolify）
- `docker compose -f coolify/docker-compose.yml config -q` → 语法/引用 OK。
- `config --services` → 仅 `skills`（`app` 正确被 `full` profile 隐藏，坐实 P1/P2 分批）。
- `docker compose ... run --rm skills /opt/runtime/run_skill.sh self-audit` → **rc=0**：证据链 30/30、血缘 FRESH、双平面四项目全绿；**台账 `+08:00`**（TZ 正确）；镜像 apt/pip/dws 层全命中 #109 缓存（零重构）。→ 证明相对挂载仓根、tar 影子绕只读、TZ 守卫、复用镜像四点在 Coolify compose 下均成立。

## 诚实边界
- **Coolify 本体未在本地测**（本机无 Coolify 实例）：compose 保持可移植（vanilla docker compose 已证），Coolify 特有的资源登记/域名/secret 注入以 README 面板步骤交付。
- 剩余为人/基建步：基建线装 Docker+Coolify、登记资源；Owner 两步（dws 设备码手机点一次、停 6 条旧排程）；一条 Cloudflare 代理 DNS。均已做成最少点击。
- fallback 路径（`skills-runtime/bootstrap.sh` + `cloudflared/`）保留但标注：同节点与 Coolify 二选一，勿并用。

## 结论
云端统一部署件按"单盘治理、不加第四件"开发完并本地实证；主路径＝Coolify。等 OVH deploy-ready（Docker/Coolify）+ Owner 两步，即可分批上线。
