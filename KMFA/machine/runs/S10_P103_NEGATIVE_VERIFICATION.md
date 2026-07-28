# S10 / P-S10-03 · T-S10-03 —— 页面、API、搜索、缓存与对象的负向验证

- 绑定验收：`AC-SEC-001`
- pass_gate：**canary 命中=0，越权读写=0**
- stop_condition：任何真实或 canary 私密数据公开可读

## canary 的价值在于「不需要任何人判断」

在私有面里埋固定标记串，在所有公开面里搜它。命中即泄露——
这个判据不依赖谁记得检查什么，**也不会因为换了个人来做而变松**。

## 扫的面不全，等于没扫

必扫八面：page / api / search / cache / object / sitemap / log / error。
少扫一个面的**表现和一切正常完全一样**，所以「面不全」本身就判失败。

## 越权部分已在 S07/T-S07-04 实测

15 条 workspace 作用域路由 × 3 种身份 = 30 条，全部 404。
404 而不是 403：403 会确认「这个 workspace 存在」，
等于免费送出一个存在性探测器。伪造凭据与无凭据给出**同样**的 404，
否则差异本身就是一个判断「token 格式对不对」的预言机。

## 实测

`tests/test_s10_s13_posture_and_release.py` + `tests/test_download_gate.py`
—— canary 命中即抛、面不全即抛、越权矩阵 30 条、报错体不回显内部细节。
