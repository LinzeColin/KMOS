# 首页本体纠偏:根路径 = KMFA 经营驾驶舱门面

- 阶段线:v1.5.2 / S03(公开根主页与 Walking Skeleton)
- 触发:Owner 2026-07-25 判定「kmfa 主页好恶心 / 这根本不是 KMFA / 一进去不应该是 KMFA 的首页吗」
- 结论:根路径 `/` 原来是一个泛化的「公开工作区」落地页(项目/上传/搜索/进度/报告/帮助),
  与 KMFA(经营驾驶舱)本体无关。本次把根路径改成 KMFA 本体门面;匿名工作区切片下沉到 `/workspace`。

## 改了什么

1. **根路径 = KMFA 首页**(`src/KmfaHome.jsx`,新增):
   - 首屏主张:「把钱、票、成本与拍板,放进同一块驾驶舱。」
   - 六个能力模块 = 驾驶舱真实页面:今天 / 回款与账龄 / 开票与税务 / 项目成本 / 待拍板 / 报告下载。
   - 四层可验证链区块(事实底账→自动核对→影响面→拍板留痕)。
   - 出口:「进入经营驾驶舱」→ `/ops/app`(私有,受 Cloudflare Access 守卫);
     「打开公开工作区」→ `/workspace`(匿名工程切片)。
   - 铁律:公开页**只讲能力、不露一个真实经营数字**;经营数据默认私有。

2. **匿名工作区迁到 `/workspace`**(原 `PublicAppShell.jsx` 不动,仅换挂载路由):
   - `src/main.jsx`:`/` → KmfaHome;`/workspace` → PublicAppShell;`/ops/app` → 私有 App。
   - 后端 `app/main.py`:新增 `/workspace`(及深链)路由,返回同一前端 index,
     `X-KMFA-Shell-Mode: public-workspace`;索引边界中间件对非根路径 fail-closed(noindex + no-store)。

3. **视觉层企业级重做**(`src/public-shell.css` + `index.html` 静态壳):
   - 明亮主题:纸白/次白分层、蓝(#2563eb)主色、卡片圆角+柔和投影、吸顶胶囊导航。
   - 全部文字仅落纯色底;配色 31+ 组数值验证 ≥ WCAG 2.2 AA(见 machine/contrast_matrix.json)。
   - CSP 自足:系统字体栈,无外链资源;装饰仅用实体边框(避开 axe 对伪元素背景不可判定的坑)。

## 真验证(非 /healthz、非纯 pytest 绿)

- 真起容器(镜像内现建前端)→ 真开页面 → 真截图:桌面/移动首页、`/workspace` 工作区,见本目录 shots/。
- `public_shell_flow.py`(桌面/移动/无 JS/降级四模式):PASS,entries=today/cash/tax/cost/decide/report。
- `public_accessibility_index.py`(chromium/firefox/webkit × axe wcag2a..22aa + robots/sitemap 边界):PASS,
  critical/serious a11y = 0;robots 拒 `/workspace`、`/api`、`/ops`、`/ui`。
- `walking_skeleton_flow.py` / `abuse_control_flow.py`:goto 路径 `/`→`/workspace`,CI(app-e2e)全环境复跑。
- 后端 pytest:158 passed(含新增 `test_workspace_route_serves_shell_with_noindex`、
  首页标题/锚点更新后的 `test_index_serves_public_shell`、`test_public_entry_contract`)。

## 边界与私有面(完工后置顶告知 Owner)

- 公开首页零经营数字;`/ops/app` 仍由 `KMFA_PRIVATE_OPS_REQUIRE_ACCESS` + Cloudflare Access 守卫。
- 本次未改任何门禁阈值、未动 append-only 台账、未改 `/ops` 与 `/api` 的私有语义。
