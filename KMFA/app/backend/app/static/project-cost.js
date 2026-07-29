/* 项目成本表的交互层：点表头排序 + 「重新计算」提交。

   ⚠️ 这个文件**必须是外链**，不能塞回 HTML 里当内联 <script>。
   本站 CSP 是 `script-src 'self'`（没有 'unsafe-inline'），而
   `style-src` 却带 'unsafe-inline' —— 内联样式生效、内联脚本被拒。
   后果极具迷惑性：⇅ 箭头在、手型光标在、hover 变色也在（都是 CSS），
   可点下去毫无反应，页面看上去完全正常。
   2026-07-29 排序与「重新计算」两个功能就是这么一起哑掉的，
   线上判据是 th 的 role=null / tabIndex=-1 —— 监听器从没挂上去过。
   门禁见 test_page_scripts_must_not_be_inline.py。 */

/* 点表头排序。数值列按 data-v 的**数值**排——按显示的千分位字符串排会让
   「1,000,000」排在「9,000」前面。空值一律沉底，不管升序降序：
   把「没有数」排到有数的前面，等于让缺失冒充最小值。 */
(function () {
  var tbl = document.getElementById('costtbl');
  if (!tbl) return;
  var heads = tbl.tHead.rows[0].cells;
  Array.prototype.forEach.call(heads, function (th, idx) {
    if (!th.hasAttribute('data-s')) return;
    th.setAttribute('role', 'button');
    th.tabIndex = 0;
    function sort() {
      var numeric = th.getAttribute('data-s') === 'n';
      var desc = th.getAttribute('aria-sort') !== 'descending';
      Array.prototype.forEach.call(heads, function (o) { o.removeAttribute('aria-sort'); });
      th.setAttribute('aria-sort', desc ? 'descending' : 'ascending');
      var body = tbl.tBodies[0];
      var rows = Array.prototype.slice.call(body.rows);
      rows.sort(function (a, b) {
        var x = a.cells[idx].getAttribute('data-v');
        var y = b.cells[idx].getAttribute('data-v');
        var ex = (x === null || x === ''), ey = (y === null || y === '');
        if (ex && ey) return 0;
        if (ex) return 1;            /* 空值永远沉底 */
        if (ey) return -1;
        if (numeric) {
          var d = parseFloat(x) - parseFloat(y);
          return desc ? -d : d;
        }
        return desc ? y.localeCompare(x, 'zh') : x.localeCompare(y, 'zh');
      });
      rows.forEach(function (r) { body.appendChild(r); });
    }
    th.addEventListener('click', sort);
    th.addEventListener('keydown', function (e) {
      if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); sort(); }
    });
  });
})();

/* 重新计算：只提交请求，真正的活在 skills 容器里跑（App 容器没有 run_skill.sh，
   也不该有——让 App 去跑克隆私有库解析上千张表，就是把「压测把线上打下线」重演一遍）。
   按钮点完立刻禁用并写明「怎么确认真的变了」——只回一句「已提交」等于没回。 */
(function () {
  var btn = document.getElementById('recalc');
  var msg = document.getElementById('recalcmsg');
  if (!btn) return;
  btn.addEventListener('click', function () {
    btn.disabled = true;
    msg.textContent = '正在提交…';
    fetch('/项目成本/重算', { method: 'POST' })
      .then(function (r) { return r.json().then(function (j) { return { ok: r.ok, j: j }; }); })
      .then(function (res) {
        if (!res.ok || !res.j['已提交']) {
          msg.textContent = '没能提交：' + (res.j['原因'] || '未知');
          btn.disabled = false;
          return;
        }
        msg.textContent = '已提交。' + res.j['说明'] + '　上次算完：' +
          (res.j['上次算完'] || '（无记录）') + '　' + res.j['怎么确认'];
      })
      .catch(function (e) {
        msg.textContent = '没能提交：' + e;
        btn.disabled = false;
      });
  });
})();
