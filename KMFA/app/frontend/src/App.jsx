import React, { useEffect, useMemo, useRef, useState } from 'react'
import * as echarts from 'echarts/core'
import { BarChart, PieChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, LegendComponent } from 'echarts/components'
import { SVGRenderer } from 'echarts/renderers'

echarts.use([BarChart, PieChart, GridComponent, TooltipComponent, LegendComponent, SVGRenderer])

function Chart({ option, height = '16rem' }) {
  const ref = useRef(null)
  useEffect(() => {
    if (!ref.current || !option) return
    // 暗色下用 echarts 内置 dark 主题：轴/文字/分割线全套跟随，背景透出卡片色
    const 暗 = window.matchMedia?.('(prefers-color-scheme: dark)').matches
    const chart = echarts.init(ref.current, 暗 ? 'dark' : null, { renderer: 'svg' })
    chart.setOption({ backgroundColor: 'transparent', ...option })
    const onResize = () => chart.resize()
    window.addEventListener('resize', onResize)
    return () => { window.removeEventListener('resize', onResize); chart.dispose() }
  }, [option])
  return <div ref={ref} style={{ width: '100%', height }} />
}

/* ---------- 通用小件 ---------- */

function Kpi({ 标, 值, 注, 色, 小 }) {
  return (
    <div className="card kpi">
      <div className="lab">{标}</div>
      <div className={`val${小 ? ' sm' : ''}${色 ? ` ${色}` : ''}`}>{值}</div>
      {注 != null && 注 !== '' && <div className="hint">{注}</div>}
    </div>
  )
}

function Tbl({ children }) {
  return <div className="tblwrap"><table className="tbl">{children}</table></div>
}

function 骨架() {
  return (
    <div aria-busy="true" aria-label="加载中">
      <div className="grid">
        {[0, 1, 2, 3].map(i => (
          <div key={i} className="card">
            <div className="skel" style={{ width: '40%', height: 12 }} />
            <div className="skel" style={{ width: '55%', height: 26, marginTop: 10 }} />
          </div>
        ))}
      </div>
      <div className="card" style={{ marginTop: 14 }}>
        {[0, 1, 2, 3, 4].map(i => (
          <div key={i} className="skel" style={{ height: 13, marginTop: i ? 12 : 2 }} />
        ))}
      </div>
    </div>
  )
}

function 加载失败卡({ 详情 }) {
  return (
    <div className="card callout bad">
      <b>这一页没取到数据</b>
      <div className="sub">{详情}</div>
      <div className="sub">刷新重试；反复出现就查对应接口与容器日志——页面不猜数据，取不到就明说。</div>
    </div>
  )
}

function 态chip(s) {
  const 色 = s === 'analyzed_open' || s === 'open' ? 'warn'
    : s === 'excluded' ? 'mut' : 'ok'
  return <span className={`chip ${色}`}>{s}</span>
}

/* ---------- 我在哪 ---------- */

function 我在哪({ 我在哪: 我, 断言, 管线, 技能 }) {
  // 三块结构与字段刻意对齐 文档/00_我在哪.md 渲染件（同源 machine/facts），验收即以其为基准
  if (!我) return <骨架 />
  if (我.加载失败) return <加载失败卡 详情={我.加载失败} />
  const 状 = 我?.当前状态
  const 卡 = 我?.卡住的事 ?? []
  const 阶段 = 我?.路线图?.阶段 ?? []
  return (
    <>
      {状 && <>
        <h3 className="sec">一、当前状态</h3>
        <Tbl><tbody>
          <tr><td className="muted" style={{ width: '9rem' }}>版本</td><td><code>{状.版本}</code></td></tr>
          <tr><td className="muted">进行到哪</td><td>
            <code>{状.阶段}</code> · <code>{状.分期}</code> · <code>{状.任务}</code></td></tr>
          <tr><td className="muted">进度</td><td>{状.进度}</td></tr>
          <tr><td className="muted">报告可信度</td><td>{状.报告可信度}</td></tr>
          <tr><td className="muted">业务结论</td><td><b>{状.业务结论}</b></td></tr>
          <tr><td className="muted">证据状态</td><td>{状.证据状态}</td></tr>
          <tr><td className="muted">卡住的事</td><td>{状.卡住件数} 件</td></tr>
        </tbody></Tbl>

        <h3 className="sec">二、卡住的事</h3>
        {卡.length === 0 ? <p className="empty">无</p> : (
          <Tbl>
            <thead><tr>
              <th>编号</th><th>什么事</th><th>谁能解</th><th>卡了多久</th>
            </tr></thead>
            <tbody>{卡.map(b => (
              <tr key={b.id}>
                <td><code>{b.id}</code></td>
                <td>{b.内容}</td>
                <td>{b.owner_only ? <span className="chip bad">只有你能解</span> : <span className="chip mut">可代办</span>}</td>
                <td>{b.首次登记}</td>
              </tr>
            ))}</tbody>
          </Tbl>
        )}

        <h3 className="sec">三、路线图（{阶段.length} 阶段）</h3>
        <Tbl>
          <thead><tr>
            <th>阶段</th><th>名称</th><th>过关标准</th><th>状态</th>
          </tr></thead>
          <tbody>{阶段.map(s => (
            <tr key={s.id}>
              <td><code>{s.id}</code></td><td>{s.name}</td>
              <td className="muted">{s.gate}</td>
              <td><span className={`chip ${s.status === '有效' ? 'ok' : 'warn'}`}>{s.status}</span></td>
            </tr>
          ))}</tbody>
        </Tbl>
        <p className="foot">更新于 {我.更新于}｜{我.同源}</p>
      </>}

      <h3 className="sec">数据面快览</h3>
      <div className="grid">
        <Kpi 标="对账断言（closed / 总数）" 值={断言 && !断言.加载失败 ? `${断言.closed} / ${断言.total}` : '…'}
             注={断言 && !断言.加载失败 ? `analyzed-open ${断言.analyzed_open}` : ''} />
        <Kpi 标="私有派生层数据行" 值={管线 && !管线.加载失败 ? (管线.staging_rows_total ?? 0).toLocaleString('zh') : '…'}
             注={管线 && !管线.加载失败 ? `截止批次 ${管线.data_as_of_batch}` : ''} />
        <Kpi 标="技能" 值={技能 && !技能.加载失败 ? 技能.count : '…'} 注="全部迁云计划中" />
      </div>
      {管线?.reconciliation_status && (
        <div className="card callout">
          <b>对账现状</b>
          <div className="sub">{管线.reconciliation_status}</div>
        </div>
      )}
      {断言?.items?.length > 0 && (
        <div className="grid">
          <div className="card">
            <div className="muted">断言状态分布</div>
            <Chart height="14rem" option={{
              tooltip: { trigger: 'item' },
              series: [{
                type: 'pie', radius: ['45%', '72%'],
                label: { formatter: '{b}\n{c}' },
                data: Object.entries(断言.items.reduce((m, i) => ((m[i.status] = (m[i.status] ?? 0) + 1), m), {}))
                  .map(([name, value]) => ({ name, value })),
              }],
            }} />
          </div>
          <div className="card">
            <div className="muted">断言按域 × 状态</div>
            <Chart height="14rem" option={(() => {
              const 域 = [...new Set(断言.items.map(i => i.domain ?? '未标域'))]
              const 态 = [...new Set(断言.items.map(i => i.status))]
              return {
                tooltip: {}, legend: { top: 0, textStyle: { fontSize: 10 } },
                grid: { left: 8, right: 8, bottom: 0, top: 44, containLabel: true },
                xAxis: { type: 'category', data: 域 },
                yAxis: { type: 'value', minInterval: 1 },
                series: 态.map(s => ({
                  name: s, type: 'bar', stack: '断言',
                  data: 域.map(d => 断言.items.filter(i => (i.domain ?? '未标域') === d && i.status === s).length),
                })),
              }
            })()} />
          </div>
        </div>
      )}
    </>
  )
}

/* ---------- 差异工作台 ---------- */

function 差异工作台({ 台, 刷新 }) {
  const [分组, set分组] = useState('全部')
  const [域, set域] = useState('全部')
  const [展开, set展开] = useState(null)
  const [理由, set理由] = useState('')
  const [忙, set忙] = useState(null)
  const [提示, set提示] = useState(null)
  if (!台) return <骨架 />
  if (台.加载失败) return <加载失败卡 详情={台.加载失败} />
  const items = 台.断言明细 ?? []
  const 域列表 = ['全部', ...new Set(items.map(i => i.域).filter(Boolean))]
  const rows = items.filter(i => (分组 === '全部' || i.分组 === 分组) && (域 === '全部' || i.域 === 域))

  async function 提交(路径, body, 键) {
    if (!理由.trim()) { set提示({ 好: false, 文: '必须写明理由——无理由的决策不留痕等于没决策' }); return }
    set忙(键); set提示(null)
    try {
      const r = await fetch(路径, { method: 'POST', headers: { 'Content-Type': 'application/json' },
                                    body: JSON.stringify({ ...body, 理由: 理由.trim() }) })
      const j = await r.json()
      if (!r.ok) { set提示({ 好: false, 文: j.detail ?? '写入失败' }); return }
      set提示({ 好: true, 文: `已追加事件 ${j.已写入?.event_id}（哈希 ${String(j.已写入?.content_hash).slice(7, 19)}…）` })
      set理由(''); await 刷新()
    } catch (e) { set提示({ 好: false, 文: String(e) }) } finally { set忙(null) }
  }

  return (
    <>
      <div className="grid">
        {['open', 'closed', 'excluded'].map(g => (
          <Kpi key={g} 标={g} 值={台.分组计数[g]} 色={g === 'open' ? 'warn' : 'ok'} />
        ))}
        <Kpi 标="决策事件" 值={台.事件.总数}
             注={`App 写入 ${台.事件['App 写入']}｜已冲正 ${台.事件.已被冲正}`} />
      </div>

      <div className="card callout ok">
        <b>写入纪律</b>
        <div className="sub">
          append-only：{台.写入纪律.append_only ? '是' : '否'}｜允许静默改写：{台.写入纪律['允许静默改写'] ? '是' : '否'}｜
          断言表可写：{台.写入纪律['断言表可写'] ? '是' : '否'}
        </div>
        <div className="sub">改主意的做法：{台.写入纪律['改主意的做法']}</div>
        <div className="sub">
          双向一致：本台孤儿事件 {台.双向一致.本台孤儿事件数} 条 → {台.双向一致.一致 ? '一致 ✅' : '不一致 ⚠️'}
          ｜仓内未挂载 {台.双向一致.仓内未挂载事件数} 条（指向治理记录号，非断言号）
        </div>
      </div>

      <div className="formrow" style={{ marginTop: 16 }}>
        <span className="muted">分组</span>
        <select className="select" value={分组} onChange={e => set分组(e.target.value)}>
          {['全部', 'open', 'closed', 'excluded'].map(d => <option key={d}>{d}</option>)}</select>
        <span className="muted">域</span>
        <select className="select" value={域} onChange={e => set域(e.target.value)}>
          {域列表.map(d => <option key={d}>{d}</option>)}</select>
        <span className="muted">{rows.length} 条</span>
      </div>

      <Tbl>
        <thead><tr>
          <th>断言</th><th>口径</th><th>期间</th>
          <th className="num">差异（元）</th><th>分组</th><th>现行决策</th>
        </tr></thead>
        <tbody>{rows.map(it => (
          <React.Fragment key={it.断言}>
            <tr className="click" onClick={() => { set展开(展开 === it.断言 ? null : it.断言); set提示(null) }}>
              <td><code>{it.断言}</code></td>
              <td>{it.口径}</td>
              <td>{it.期间}</td>
              <td className={`num${it.差异元 === null ? '' : ' tone-warn'}`}>
                {it.差异元 === null ? '—' : `¥${it.差异元}`}</td>
              <td>{态chip(it.分组)}</td>
              <td>{it.现行决策
                ? <span><b>{it.现行决策.决策}</b> → {it.现行决策.到状态}</span>
                : <span className="muted">未决策</span>}</td>
            </tr>
            {展开 === it.断言 && (
              <tr className="detail"><td colSpan={6}>
                <div style={{ marginBottom: 10 }}>{it.结论 ?? '（无 finding）'}</div>
                <div className="formrow" style={{ marginTop: 0 }}>
                  <input className="input" style={{ flex: '1 1 22rem', minWidth: '14rem' }}
                         placeholder="决策理由（必填，会连同事件一起留痕）"
                         value={理由} onChange={e => set理由(e.target.value)} />
                  {台.决策入口.map(d => (
                    <button key={d.决策} type="button" className="btn" disabled={忙 !== null}
                            onClick={() => 提交('/api/差异工作台/决策',
                              { 断言: it.断言, 决策: d.决策 }, `${it.断言}-${d.决策}`)}>
                      {忙 === `${it.断言}-${d.决策}` ? '写入中…' : `${d.决策} → ${d.到状态}`}
                    </button>
                  ))}
                </div>
                {提示 && <div className={`alert ${提示.好 ? 'ok' : 'bad'}`}>{提示.文}</div>}
                {it.决策事件.length > 0 && (
                  <Tbl>
                    <thead><tr>
                      <th>事件号</th><th>决策</th><th>理由</th>
                      <th>时间</th><th>来源</th><th>操作</th>
                    </tr></thead>
                    <tbody>{it.决策事件.map(e => (
                      <tr key={e.事件号} className={e.已被冲正 ? 'dim' : ''}>
                        <td><code>{e.事件号}</code></td>
                        <td>{e.决策 ?? e.动作}{e.已被冲正 && ' （已冲正）'}
                          {e.冲正的是 && <span className="muted"> 冲正 {e.冲正的是}</span>}</td>
                        <td>{e.理由}</td>
                        <td className="muted">{e.时间}</td>
                        <td className="muted">{e.来源}</td>
                        <td>{(!e.已被冲正 && !e.冲正的是 && e.来源 !== '仓内治理面（只读）') ? (
                          <button type="button" className="btn danger" disabled={忙 !== null}
                                  onClick={() => 提交('/api/差异工作台/冲正',
                                    { 冲正事件号: e.事件号 }, `rev-${e.事件号}`)}>
                            {忙 === `rev-${e.事件号}` ? '写入中…' : '冲正'}
                          </button>) : <span className="muted">—</span>}</td>
                      </tr>
                    ))}</tbody>
                  </Tbl>
                )}
              </td></tr>
            )}
          </React.Fragment>
        ))}</tbody>
      </Tbl>
    </>
  )
}

/* ---------- 报告中心 ---------- */

function 报告中心({ 中心 }) {
  if (!中心) return <骨架 />
  if (中心.加载失败) return <加载失败卡 详情={中心.加载失败} />
  const 水 = 中心.水印, 判 = 中心.交付判据
  return (
    <>
      <div className="grid">
        <Kpi 标="报告等级" 值={中心.页眉.报告等级} 色="bad" />
        <Kpi 标="质量等级" 值={中心.页眉.质量等级} />
        <Kpi 标="delivery 状态" 值={中心.页眉.delivery状态} 小
             色={判.delivery_allowed ? 'ok' : 'bad'} />
        <Kpi 标="导出登记" 值={中心.导出登记.条数} 注="追加式，不可改写" />
      </div>

      <div className="card callout bad">
        <b>水印：{水.生效中 ? '生效中，且无法关闭' : '已解除'}</b>
        {水.文案 && <div className="sub" style={{ fontFamily: 'var(--mono)' }}>{水.文案}</div>}
        <div className="sub">覆盖格式：{水.覆盖格式.join(' / ')}｜可关闭：{水.可关闭 ? '是' : '否'}</div>
        <div className="sub">去除条件：{水.去除条件}</div>
      </div>

      <h3 className="sec">八份报告 × 三格式</h3>
      <Tbl>
        <thead><tr>
          <th>号</th><th>标题</th><th className="num">正文字数</th><th>下载</th>
        </tr></thead>
        <tbody>{中心.报告.map(r => (
          <tr key={r.编号}>
            <td>{r.编号}</td>
            <td>{r.标题}</td>
            <td className="num">{r.正文字数.toLocaleString('zh')}</td>
            <td>{r.格式.map(f => (
              <a key={f.格式} href={f.下载} style={{ marginRight: '.8rem' }}
                 title={f.可提交公开仓 ? '公开安全，可提交' : '仅运行时生成，不入公开仓'}>
                {f.格式.toUpperCase()}{f.可提交公开仓 ? '' : '（运行时）'}
              </a>
            ))}</td>
          </tr>
        ))}</tbody>
      </Tbl>

      <h3 className="sec">PDF 策略</h3>
      <div className="card callout warn" style={{ marginTop: 12 }}>
        <div>{中心.PDF策略.说明}</div>
        <div className="sub">中文渲染：{中心.PDF策略.中文渲染}</div>
      </div>

      {中心.导出登记.记录.length > 0 && (
        <>
          <h3 className="sec">导出 hash 登记（最近 {中心.导出登记.记录.length} 条）</h3>
          <Tbl>
            <thead><tr>
              <th>号</th><th>格式</th><th>sha256</th>
              <th className="num">字节</th><th>水印</th><th>时间</th>
            </tr></thead>
            <tbody>{中心.导出登记.记录.slice().reverse().map((e, i) => (
              <tr key={i}>
                <td>{e.报告}</td>
                <td>{e.格式.toUpperCase()}</td>
                <td><code style={{ fontSize: '.72rem' }}>{String(e.sha256).slice(7, 27)}…</code></td>
                <td className="num">{(e.字节 ?? 0).toLocaleString('zh')}</td>
                <td>{e.水印已加 ? <span className="chip bad">已加</span> : <span className="chip ok">无</span>}</td>
                <td className="muted">{e.导出时间}</td>
              </tr>
            ))}</tbody>
          </Tbl>
        </>
      )}
    </>
  )
}

/* ---------- 影响重跑 ---------- */

function 影响重跑({ 图, 选中资产, 选资产, 刷新 }) {
  const [理由, set理由] = useState('')
  const [忙, set忙] = useState(false)
  const [结果, set结果] = useState(null)
  const [提示, set提示] = useState(null)
  if (!图) return <骨架 />
  if (图.加载失败) return <加载失败卡 详情={图.加载失败} />
  const 下 = 图.选中

  async function 重跑() {
    if (!理由.trim()) { set提示({ 好: false, 文: '必须写明重跑理由' }); return }
    set忙(true); set提示(null)
    try {
      const r = await fetch('/api/影响重跑/重跑', { method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 资产: 选中资产, 理由: 理由.trim() }) })
      const j = await r.json()
      if (!r.ok) { set提示({ 好: false, 文: j.detail ?? '重跑失败' }); return }
      set结果(j); set理由('')
      set提示({ 好: true, 文: `轮次 ${j.轮次号} 完成：${j.步骤数} 层，耗时 ${j.耗时秒}s，旧版本全保留=${j.旧版本全保留}` })
      await 刷新(选中资产)
    } catch (e) { set提示({ 好: false, 文: String(e) }) } finally { set忙(false) }
  }

  return (
    <>
      <div className="grid">
        <Kpi 标="血缘节点 / 边" 值={`${图.血缘.节点数} / ${图.血缘.边数}`} />
        <Kpi 标="可选资产" 值={图.血缘.可选资产数} />
        <Kpi 标="本机重跑轮次" 值={图.本机重跑记录.轮次} 注={`${图.本机重跑记录.步骤数} 步留痕`} />
        <Kpi 标="仓内既有留痕" 值={图.既有仓内留痕.重跑步骤} 注={`影响预览 ${图.既有仓内留痕.影响预览}`} />
      </div>

      <div className="card callout ok">
        <b>重跑纪律</b>
        <div className="sub">
          覆盖旧版本：{图.重跑纪律.覆盖旧版本 ? '是' : '否'}｜旧版本处置：<code>{图.重跑纪律.旧版本处置}</code>｜
          raw 层可写：{图.重跑纪律.raw层可写 ? '是' : '否'}｜
          允许借重跑升报告等级：{图.重跑纪律.允许借重跑升报告等级 ? '是' : '否'}
        </div>
        <div className="sub">{图.重跑纪律.留痕}</div>
      </div>

      <h3 className="sec">① 选中资产</h3>
      {/* 本页第一个 select 必须是资产选择器——E2E 用 select.first 选中它，别在它前面加任何 select */}
      <select className="select" style={{ minWidth: '22rem', marginTop: 10 }} value={选中资产 ?? ''}
              onChange={e => { 选资产(e.target.value); set结果(null); set提示(null) }}>
        <option value="">— 选一个原始资产 —</option>
        {图.血缘.资产.map(a => (
          <option key={a.资产} value={a.资产}>{a.资产}（{a.域}，{a.派生表数} 张派生表）</option>
        ))}
      </select>

      {下 && (
        <>
          <h3 className="sec">② 下游影响面（由血缘边算出）</h3>
          <Tbl>
            <thead><tr><th>派生表</th><th className="num">行数</th><th>版本</th></tr></thead>
            <tbody>{下.派生表.map(t => (
              <tr key={t.表}><td><code>{t.表}</code></td>
                <td className="num">{(t.行数 ?? 0).toLocaleString('zh')}</td>
                <td className="muted">{t.版本 ?? '—'}</td></tr>
            ))}</tbody>
          </Tbl>
          <div className="card" style={{ marginTop: 12 }}>
            <div>受影响视图：{下.受影响视图.length ? 下.受影响视图.join('、') : '—'}</div>
            <div style={{ marginTop: 4 }}>受影响断言域：{下.受影响断言域.join('、') || '—'}</div>
            <div style={{ marginTop: 4 }}>受影响报告：{下.受影响报告.join('、') || '—'}</div>
          </div>

          <h3 className="sec">③ 发起重跑</h3>
          <div className="formrow">
            <input className="input" style={{ flex: '1 1 22rem' }} placeholder="重跑理由（必填，会连同每层留痕）"
                   value={理由} onChange={e => set理由(e.target.value)} />
            <button type="button" className="btn pri" disabled={忙} onClick={重跑}>
              {忙 ? '重跑中…' : '发起重跑（四层链）'}</button>
          </div>
          {提示 && <div className={`alert ${提示.好 ? 'ok' : 'bad'}`}>{提示.文}</div>}
        </>
      )}

      {结果 && (
        <>
          <h3 className="sec">④ 本次重跑结果（轮次 {结果.轮次号}）</h3>
          <Tbl>
            <thead><tr><th>序</th><th>层</th><th>内容哈希</th><th>新版本</th></tr></thead>
            <tbody>{结果.各层.map(s => (
              <tr key={s.序}>
                <td>{s.序}</td>
                <td>{s.名称}<br /><code style={{ fontSize: '.72rem', opacity: .75 }}>{s.层}</code></td>
                <td><code style={{ fontSize: '.72rem' }}>{String(s.哈希).slice(7, 27)}…</code></td>
                <td><code style={{ fontSize: '.7rem' }}>{String(s.新版本).split('/').pop()}</code></td>
              </tr>
            ))}</tbody>
          </Tbl>
          <div className="card" style={{ marginTop: 12 }}>
            链完整：{结果.链完整 ? '是 ✅' : '否 ⚠️'}｜旧版本全保留：{结果.旧版本全保留 ? '是 ✅' : '否 ⚠️'}｜
            耗时 {结果.耗时秒}s｜留痕：<code>{结果.留痕位置}</code>
          </div>
        </>
      )}

      {图.本机重跑记录.最近.length > 0 && (
        <>
          <h3 className="sec">历史重跑</h3>
          <Tbl>
            <thead><tr><th>轮次号</th><th>步骤</th><th>状态</th><th>起止</th></tr></thead>
            <tbody>{图.本机重跑记录.最近.slice().reverse().map(r => (
              <tr key={r.轮次号}>
                <td><code>{r.轮次号}</code></td>
                <td>{r.步骤}</td>
                <td><span className={`chip ${r.状态 === 'completed' ? 'ok' : 'warn'}`}>{r.状态}</span></td>
                <td className="muted">{r.起于} → {r.止于}</td>
              </tr>
            ))}</tbody>
          </Tbl>
        </>
      )}
    </>
  )
}

/* ---------- 审计日志 ---------- */

function 审计日志({ 审计 }) {
  if (!审计) return <骨架 />
  if (审计.加载失败) return <加载失败卡 详情={审计.加载失败} />
  const 契 = 审计.契约, 访 = 审计.访问模式
  return (
    <>
      <div className="grid">
        <Kpi 标="审计事件总数" 值={审计.总数} 注="append-only" />
        {Object.entries(审计.按动作).slice(0, 3).map(([k, v]) => (
          <Kpi key={k} 标={k} 值={v} />
        ))}
      </div>

      <div className="card callout ok">
        <b>访问模式：{访.模式}</b>
        <div className="sub">应用内登录：{访.应用内登录 ? '有' : '无'}｜生产鉴权：{访.生产鉴权}</div>
        <div className="sub">角色口径：{访.角色口径.join('、')}</div>
        <div className="sub">{访.说明}</div>
      </div>

      <div className="card callout warn">
        <b>审计契约（承接 v014 S17）</b>
        <div className="sub">
          政策版本 <code>{契.政策版本}</code>｜append-only：{契.append_only ? '是' : '否'}｜
          允许记原始载荷：{契.允许记原始载荷 ? '是' : '否'}｜允许记业务明文：{契.允许记业务明文 ? '是' : '否'}
        </div>
        <div className="sub">必填字段：{契.必填字段.join('、')}</div>
        <div className="sub">动作类型：{契.动作类型.join('、')}</div>
      </div>

      <h3 className="sec">事件流水（最近在前）</h3>
      {审计.事件.length === 0 ? <p className="empty">暂无事件——做一次决策或导出后即会留痕。</p> : (
        <Tbl>
          <thead><tr>
            <th>时间</th><th>动作</th><th>对象</th>
            <th>结果</th><th>角色</th><th>证据</th>
          </tr></thead>
          <tbody>{审计.事件.map(e => (
            <tr key={e.event_id}>
              <td className="muted">{e.event_time}</td>
              <td><code>{e.action_type}</code></td>
              <td>{e.subject_ref}</td>
              <td><span className={`chip ${/OK|COMPLETED/.test(e.result_status) ? 'ok' : 'warn'}`}>{e.result_status}</span></td>
              <td>{e.actor_role}</td>
              <td><code style={{ fontSize: '.7rem' }}>{String(e.evidence_ref).split('/').pop()}</code></td>
            </tr>
          ))}</tbody>
        </Tbl>
      )}
    </>
  )
}

/* ---------- 排程健康 ---------- */

function 排程健康({ 排程 }) {
  if (!排程) return <骨架 />
  if (排程.加载失败) return <加载失败卡 详情={排程.加载失败} />
  if (!排程.可读) return (
    <div className="card callout bad">
      <b>读不到排程日志</b>
      <div className="sub">{排程.原因}</div>
      <div className="sub">{排程.诚实边界}</div>
    </div>
  )
  const 好 = 排程.失败数 === 0 && 排程.仍在空跑数 === 0
  return (
    <>
      <div className="grid">
        <Kpi 标="有记录的技能" 值={排程.有记录的技能数} />
        <Kpi 标="最近一次失败" 值={排程.失败数} 色={排程.失败数 ? 'bad' : 'ok'} />
        <Kpi 标="仍在空跑" 值={排程.仍在空跑数} 色={排程.仍在空跑数 ? 'warn' : 'ok'} 注="投递开关=0" />
        <Kpi 标="总执行次数" 值={排程.总执行次数} />
      </div>
      <div className={`card callout ${好 ? 'ok' : 'warn'}`}>
        <b>{排程.结论}</b>
        <div className="sub">{排程.诚实边界}</div>
      </div>
      <Tbl>
        <thead><tr>
          <th>技能</th><th>约定时刻</th><th>最近一次</th>
          <th className="num">距今</th><th>结果</th><th>投递</th>
        </tr></thead>
        <tbody>{排程.逐项.map(x => (
          <tr key={x.技能}>
            <td><code>{x.技能}</code></td>
            <td className="muted">{x.约定时刻}</td>
            <td>{x.最近一次 ?? <span className="tone-bad">从未跑过</span>}</td>
            <td className="num">{x.距今小时 == null ? '—' : `${x.距今小时} 小时前`}</td>
            <td>{x.成功 === true ? <span className="chip ok">成功 (rc=0)</span>
              : x.成功 === false ? <span className="chip bad">失败 (rc={x.退出码})</span>
              : <span className="muted">—</span>}</td>
            <td>{x.投递开关 == null ? <span className="muted">—</span>
              : String(x.投递开关) === '1' ? <span className="chip ok">已开</span>
              : <span className="chip warn">空跑</span>}</td>
          </tr>
        ))}</tbody>
      </Tbl>
    </>
  )
}

/* ---------- 数据管线 ---------- */

function 数据管线({ 管线 }) {
  if (!管线) return <骨架 />
  if (管线.加载失败) return <加载失败卡 详情={管线.加载失败} />
  const 表 = Object.entries(管线.staging_tables ?? {}).sort((a, b) => (b[1].rows ?? 0) - (a[1].rows ?? 0))
  return (
    <>
      <div className="grid">
        <Kpi 标="接入原始文件" 值={管线.raw_assets_registered ?? '—'} 注="内容寻址入仓（KMDatabase/data）" />
        <Kpi 标="派生层数据行" 值={(管线.staging_rows_total ?? 0).toLocaleString('zh')}
             注={`截止批次 ${管线.data_as_of_batch}`} />
        <Kpi 标="质量档位" 值={管线.quality_grade_current ?? '—'} 小
             注={`未决质量卡点 ${管线.quality_blockers_open ?? 0} 项`} />
      </div>
      <div className="card" style={{ marginTop: 14 }}>
        <div className="muted">派生层各表行数（对数轴）</div>
        <Chart height={`${Math.max(表.length * 1.7, 10)}rem`} option={{
          tooltip: {}, grid: { left: 8, right: 48, top: 8, bottom: 8, containLabel: true },
          xAxis: { type: 'log', minorSplitLine: { show: false } },
          yAxis: { type: 'category', data: 表.map(([名]) => 名).reverse(), axisLabel: { fontSize: 10 } },
          series: [{ type: 'bar', data: 表.map(([, 值]) => 值.rows ?? 0).reverse(),
            label: { show: true, position: 'right', formatter: p => p.value.toLocaleString('zh') } }],
        }} />
      </div>
      <h3 className="sec">派生层各表（私有 DuckDB，可由工具链零重建）</h3>
      <Tbl>
        <thead><tr><th>表</th><th className="num">行数</th></tr></thead>
        <tbody>
          {表.map(([名, 值]) => (
            <tr key={名}><td>{名}</td>
              <td className="num">{(值.rows ?? 0).toLocaleString('zh')}</td></tr>
          ))}
        </tbody>
      </Tbl>
      {管线.reconciliation_status && (
        <div className="card callout">
          <b>对账现状</b>
          <div className="sub">{管线.reconciliation_status}</div>
        </div>
      )}
      {Array.isArray(管线.next_gates) && 管线.next_gates.length > 0 && (
        <div className="card" style={{ marginTop: 14 }}>
          <div className="muted">下一步门禁</div>
          <ul className="muted">
            {管线.next_gates.map((g, i) => <li key={i}>{typeof g === 'string' ? g : JSON.stringify(g)}</li>)}
          </ul>
        </div>
      )}
      <div className="foot">血缘：{管线.lineage ?? '—'}</div>
    </>
  )
}

/* ---------- 技能 ---------- */

function 技能页({ 技能 }) {
  const [展开, set展开] = useState(null)
  if (!技能) return <骨架 />
  if (技能.加载失败) return <加载失败卡 详情={技能.加载失败} />
  const rows = 技能.skills ?? []
  return (
    <>
      <div className="card callout" style={{ marginTop: 18 }}>
        <b>运行策略</b>
        <div className="sub">
          全部 {技能.count} 项技能依赖云端运行（Oracle 基座 <code>KMFA/deploy/skills-runtime/</code>）；
          本机不常驻。等待实例开通后按运行手册上云，测试收发对象「张霖泽」。
        </div>
      </div>
      <Tbl>
        <thead><tr><th>技能</th><th>排程</th><th>外部依赖</th><th>迁移待办</th></tr></thead>
        <tbody>
          {rows.map(it => (
            <React.Fragment key={it.id}>
              <tr className="click" onClick={() => set展开(展开 === it.id ? null : it.id)}>
                <td>{it.名称 ?? it.id}</td>
                <td className="muted">{(it.排程 ?? []).length ? it.排程.join('、') : '—'}</td>
                <td className="muted">{(it.外部依赖 ?? []).length ? it.外部依赖.join('、') : '—'}</td>
                <td>{it.本地路径硬编码 > 0
                  ? <span className="chip warn">本地路径硬编码 {it.本地路径硬编码} 处</span>
                  : <span className="chip ok">无</span>}</td>
              </tr>
              {展开 === it.id && (
                <tr className="detail"><td colSpan={4}>
                  <div>{it.用途 ?? '（登记表无用途描述）'}</div>
                  <div className="muted" style={{ marginTop: 4 }}>机器 id：{it.id}｜登记状态：{it.登记状态 ?? '—'}</div>
                </td></tr>
              )}
            </React.Fragment>
          ))}
        </tbody>
      </Tbl>
    </>
  )
}

/* ---------- 源检查板 ---------- */

function 源检查板({ 源检查 }) {
  if (!源检查) return <骨架 />
  if (源检查.加载失败) return <加载失败卡 详情={源检查.加载失败} />
  const 协议 = 源检查.矩阵协议, 覆盖 = 源检查.覆盖矩阵, 鲜 = 源检查.新鲜度, 派生 = 源检查.派生层
  return (
    <>
      <div className="grid">
        <Kpi 标="登记资产" 值={覆盖.资产合计} />
        <Kpi 标="数据批次" 值={鲜.数据批次 || '—'} 小 />
        <Kpi 标="派生表 / 行" 值={`${派生.表数} / ${(派生.行合计 ?? 0).toLocaleString('zh')}`} />
        <Kpi 标="新鲜度" 值={鲜.stale ? 'STALE' : 'FRESH'} 色={鲜.stale ? 'bad' : 'ok'} />
      </div>
      <p className="muted" style={{ marginTop: 10 }}>{鲜.提示}｜血缘批次：{(鲜.血缘批次 || []).join('、') || '—'}</p>

      <h3 className="sec">覆盖矩阵：源 × 登记状态</h3>
      <Tbl>
        <thead>
          <tr>
            <th>源</th>
            {覆盖.状态列.map(s => <th key={s} className="num">{s}</th>)}
            <th className="num">合计</th>
          </tr>
        </thead>
        <tbody>
          {覆盖.行.map(r => (
            <tr key={r.源}>
              <td>{r.源}</td>
              {覆盖.状态列.map(s => <td key={s} className="num">{r[s] ?? 0}</td>)}
              <td className="num" style={{ fontWeight: 700 }}>{r.合计}</td>
            </tr>
          ))}
        </tbody>
      </Tbl>

      <h3 className="sec">正式源检查矩阵（协议态）</h3>
      <Tbl>
        <tbody>
          <tr><td className="muted" style={{ width: '9rem' }}>schema</td><td>{协议.schema || '—'}</td></tr>
          <tr><td className="muted">阶段</td><td>{协议.阶段 || '—'}</td></tr>
          <tr><td className="muted">状态</td><td>{协议.状态 || '—'}</td></tr>
          <tr><td className="muted">已提交源行</td>
            <td className={协议.已提交源行 ? '' : 'tone-warn'} style={{ fontWeight: 700 }}>{协议.已提交源行}</td></tr>
          <tr><td className="muted">必需维度</td><td>{(协议.必需维度 || []).join('、')}</td></tr>
          <tr><td className="muted">允许状态</td><td>{(协议.允许状态 || []).join('、')}</td></tr>
        </tbody>
      </Tbl>
      <p className="foot">{协议.说明}</p>
    </>
  )
}

/* ---------- 账龄回款 ---------- */

function 账龄回款({ 账龄 }) {
  if (!账龄) return <骨架 />
  if (账龄.加载失败) return <加载失败卡 详情={账龄.加载失败} />
  const 对 = 账龄.回款对账, 恒 = 账龄.账龄恒等式, 构 = 账龄.账龄结构层
  return (
    <>
      <div className="grid">
        <Kpi 标="回款对账月数" 值={对.月数} />
        <Kpi 标="零分差月数" 值={对.零分差月数} 色="ok" />
        <Kpi 标="未闭月数" 值={对.未闭月数} 色={对.未闭月数 ? 'warn' : 'ok'} />
        <Kpi 标="最大差异" 值={对.最大差异 ? `¥${对.最大差异.差异元}` : '—'} 注={对.最大差异?.期间 ?? ''} />
      </div>

      <h3 className="sec">回款逐月对账（真实分差）</h3>
      <Tbl>
        <thead><tr>
          <th>断言</th><th>口径</th><th>期间</th>
          <th className="num">差异（元）</th><th className="num">差异（分）</th><th>状态</th>
        </tr></thead>
        <tbody>{对.逐月.map(m => (
          <tr key={m.断言}>
            <td><code>{m.断言}</code></td>
            <td>{m.口径}</td>
            <td>{m.期间}</td>
            <td className={`num ${m.差异分 ? 'tone-warn' : 'tone-ok'}`}
                style={{ fontWeight: m.差异分 ? 700 : 400 }}>
              {m.差异元 === null ? '—' : `¥${m.差异元}`}</td>
            <td className="num">{m.差异分 ?? '—'}</td>
            <td>{态chip(m.状态)}</td>
          </tr>
        ))}</tbody>
      </Tbl>

      <h3 className="sec">账龄恒等式</h3>
      <Tbl>
        <thead><tr><th>断言</th><th>口径</th><th>快照</th>
          <th className="num">差异分</th><th>状态</th></tr></thead>
        <tbody>{恒.map(r => (
          <tr key={r.断言}>
            <td><code>{r.断言}</code></td><td>{r.口径}</td>
            <td className="muted">{r.快照}</td>
            <td className={`num ${r.差异分 === 0 ? 'tone-ok' : 'tone-warn'}`}>{r.差异分}</td>
            <td>{态chip(r.状态)}</td>
          </tr>
        ))}</tbody>
      </Tbl>

      <h3 className="sec">账龄结构层（值仍被阻断）</h3>
      <div className="card callout warn" style={{ marginTop: 12 }}>
        <div>{账龄.诚实边界}</div>
        <div className="sub">
          源泳道 {构.源泳道数} 条，状态 <code>{构.泳道数据状态.join('、')}</code>；
          优先事项 {构.优先事项数} 条（匿名指针）；允许作经营依据：{构.允许作经营依据 ? '是' : '否'}
        </div>
      </div>
      <ul className="muted">{构.限制.map((t, i) => <li key={i}>{t}</li>)}</ul>

      <h3 className="sec">派生层规模</h3>
      <Tbl>
        <thead><tr><th>staging 表</th><th className="num">真实行数</th></tr></thead>
        <tbody>{账龄.派生层规模.map(t => (
          <tr key={t.表}><td><code>{t.表}</code></td>
            <td className="num">{(t.行数 ?? 0).toLocaleString('zh')}</td></tr>
        ))}</tbody>
      </Tbl>
    </>
  )
}

/* ---------- 断言表（开票纳税三个域共用） ---------- */

function 断言表({ 块, 标题 }) {
  return (
    <>
      <h3 className="sec">{标题}（真实分差 {块.条数} 条）</h3>
      <Tbl>
        <thead><tr>
          <th>断言</th><th>口径</th><th>期间</th>
          <th className="num">差异（元）</th><th className="num">差异（分）</th><th>状态</th>
        </tr></thead>
        <tbody>{块.逐条.map(r => (
          <tr key={r.断言}>
            <td><code>{r.断言}</code></td>
            <td>{r.口径}</td>
            <td>{r.期间}</td>
            <td className={`num ${r.差异分 ? 'tone-warn' : 'tone-ok'}`}
                style={{ fontWeight: r.差异分 ? 700 : 400 }}>
              {r.差异元 === null ? '—' : `¥${r.差异元}`}</td>
            <td className="num">{r.差异分 ?? '—'}</td>
            <td>{态chip(r.状态)}</td>
          </tr>
        ))}</tbody>
      </Tbl>
      {块.逐条.filter(r => r.结论).map(r => (
        <details key={r.断言}>
          <summary><code>{r.断言}</code> 结论</summary>
          <div className="muted" style={{ marginTop: 6, lineHeight: 1.6 }}>{r.结论}</div>
        </details>
      ))}
    </>
  )
}

/* ---------- 开票纳税 ---------- */

function 开票纳税({ 开票 }) {
  if (!开票) return <骨架 />
  if (开票.加载失败) return <加载失败卡 详情={开票.加载失败} />
  const 红 = 开票.红线, 构 = 开票.结构层, 政 = 开票.税务政策证据
  const 红线项 = Object.entries(红)
  const 红线全零 = 红线项.every(([, v]) => v === 0)
  const 全部方法 = Object.entries(构).flatMap(([组, v]) => (v.方法 || []).map(m => ({ ...m, 组 })))
  return (
    <>
      <div className="grid">
        <Kpi 标="开票域断言" 值={开票.开票对账.条数} 注={`未闭 ${开票.开票对账.未闭条数}`} />
        <Kpi 标="税务域断言" 值={开票.税务对账.条数} 注={`未闭 ${开票.税务对账.未闭条数}`} />
        <Kpi 标="贷款域断言" 值={开票.贷款对账.条数} 注={`零分差 ${开票.贷款对账.零分差条数}`} />
        <Kpi 标="红线动作合计" 值={红线项.reduce((a, [, v]) => a + (v ?? 0), 0)}
             色={红线全零 ? 'ok' : 'bad'} 注="不开票·不申报·不动账" />
      </div>

      <断言表 块={开票.开票对账} 标题="开票对账" />
      <断言表 块={开票.税务对账} 标题="税务对账" />
      <断言表 块={开票.贷款对账} 标题="贷款对账" />

      <h3 className="sec">红线：本页只读，不产生任何业务动作</h3>
      <Tbl>
        <thead><tr><th>动作</th><th className="num">事实计数</th></tr></thead>
        <tbody>{红线项.map(([k, v]) => (
          <tr key={k}><td>{k}</td>
            <td className={`num ${v === 0 ? 'tone-ok' : 'tone-bad'}`} style={{ fontWeight: 700 }}>{v}</td></tr>
        ))}</tbody>
      </Tbl>

      <h3 className="sec">计划层（值仍被阻断，故不出计划金额）</h3>
      <div className="card callout warn" style={{ marginTop: 12 }}>
        <div>{开票.诚实边界}</div>
      </div>
      <Tbl>
        <thead><tr><th>计划段</th><th>决策</th>
          <th className="num">已证值绑定车道</th><th className="num">公开业务金额</th>
          <th>车道</th></tr></thead>
        <tbody>{Object.entries(构).map(([名, v]) => (
          <tr key={名}>
            <td>{名}</td>
            <td className="tone-warn">{v.决策}</td>
            <td className="num">{v.已证值绑定车道数}</td>
            <td className="num">{v.公开业务金额数}</td>
            <td className="muted">{(v.车道 || []).map(l => l.车道).join('、')}</td>
          </tr>
        ))}</tbody>
      </Tbl>

      <h4 className="sec">九个方法的阻断原因（定义已完备，缺权威值绑定）</h4>
      <Tbl>
        <thead><tr><th>方法</th><th>定义完备</th>
          <th>产出状态</th><th>依赖车道</th><th>还缺什么</th></tr></thead>
        <tbody>{全部方法.map(m => (
          <tr key={`${m.组}-${m.方法}`}>
            <td>{m.名称 ?? m.方法}<br />
              <code style={{ fontSize: '.75rem', opacity: .75 }}>{m.方法}</code></td>
            <td>{m.定义完备 ? <span className="chip ok">是</span> : <span className="chip warn">否</span>}</td>
            <td className="tone-warn">{m.产出状态}</td>
            {/* 相邻 <code> 之间要有真实空白节点：只靠 margin 时 innerText/复制会粘连成一个词 */}
            <td>{(m.依赖车道 || []).map((l, i) => (
              <React.Fragment key={l}>{i > 0 && ' '}<code>{l}</code></React.Fragment>))}</td>
            <td className="muted">{m.说明}</td>
          </tr>
        ))}</tbody>
      </Tbl>

      <h3 className="sec">
        税务政策：证据缺口与风险提示（{政.证据完备项目数}/{政.项目数} 证据完备，不作资格判断）
      </h3>
      <Tbl>
        <thead><tr><th>项目</th><th>风险等级</th>
          <th>风险提示</th><th>证据缺口</th></tr></thead>
        <tbody>{政.逐项.map(p => (
          <tr key={p.项目}>
            <td>{p.项目}</td>
            <td><span className={`chip ${p.风险等级 === 'high' ? 'bad' : 'warn'}`}>{p.风险等级}</span></td>
            <td>{p.风险提示}</td>
            <td>{p.证据缺口}</td>
          </tr>
        ))}</tbody>
      </Tbl>

      <h3 className="sec">派生层规模</h3>
      <Tbl>
        <thead><tr><th>staging 表</th><th className="num">真实行数</th></tr></thead>
        <tbody>{开票.派生层规模.map(t => (
          <tr key={t.表}><td><code>{t.表}</code></td>
            <td className="num">{(t.行数 ?? 0).toLocaleString('zh')}</td></tr>
        ))}</tbody>
      </Tbl>
    </>
  )
}

/* ---------- 项目成本 ---------- */

function 项目成本({ 成本 }) {
  if (!成本) return <骨架 />
  if (成本.加载失败) return <加载失败卡 详情={成本.加载失败} />
  const 层 = 成本.事实层, 构 = 成本.必需结构, 阻 = 成本.阻塞链
  const 阻塞中 = 层.已算金额记录数 === 0
  return (
    <>
      {阻塞中 && (
        <div className="card callout warn">
          <b>金额尚不可计算——本页不产出任何毛利数字</b>
          <div className="sub">{成本.诚实边界}</div>
        </div>
      )}
      <div className="grid">
        <Kpi 标="事实层记录" 值={层.记录数} 注={`已算金额 ${层.已算金额记录数}`} />
        <Kpi 标="成本类别槽位" 值={构.成本类别.length} />
        <Kpi 标="事实指标槽位" 值={构.事实指标.length} />
      </div>
      <p className="muted" style={{ marginTop: 10 }}>
        状态 <code>{层.状态}</code>｜公式 {层.公式版本}｜映射 {层.映射版本}｜生成于 {层.生成于}</p>

      <h3 className="sec">成本类别 × 事实指标（结构骨架）</h3>
      <p className="muted" style={{ marginTop: 8 }}>成本类别：{构.成本类别.join('、')}</p>
      <p className="muted" style={{ marginTop: 4 }}>事实指标：{构.事实指标.join('、')}</p>

      <h3 className="sec">事实记录</h3>
      <Tbl>
        <thead><tr>
          <th>记录号</th><th>项目实体</th><th>计算状态</th>
          <th>金额已计算</th><th>成本/指标槽位</th><th>已登记哈希</th>
          <th>明文已公开</th>
        </tr></thead>
        <tbody>{成本.记录.map(r => (
          <tr key={r.记录号}>
            <td><code>{r.记录号}</code></td>
            <td><code>{r.项目实体}</code></td>
            <td className="tone-warn">{r.计算状态}</td>
            <td>{r.金额已计算 ? '是' : '否'}</td>
            <td className="num">{r.成本槽位} / {r.指标槽位}</td>
            <td className="num">{r.已登记哈希}</td>
            <td>{r.明文已公开 ? '是' : '否（仅私有面）'}</td>
          </tr>
        ))}</tbody>
      </Tbl>

      <h3 className="sec">阻塞链</h3>
      <p className="muted" style={{ marginTop: 8 }}>{阻.直接原因}｜基准 <code>{阻.基准引用}</code></p>
      <Tbl>
        <thead><tr><th>编号</th><th>根阻塞</th><th>谁能解</th><th>已卡</th></tr></thead>
        <tbody>{阻.根阻塞.map(b => (
          <tr key={b.编号}>
            <td><code>{b.编号}</code></td><td>{b.内容}</td>
            <td>{b.只有Owner可解 ? <span className="chip bad">只有你能解</span> : <span className="chip mut">可代办</span>}</td>
            <td>{b.已卡}</td>
          </tr>
        ))}</tbody>
      </Tbl>

      <h3 className="sec">可下钻派生层（A0 就位后据此归集）</h3>
      <Tbl>
        <thead><tr><th>staging 表</th><th className="num">真实行数</th></tr></thead>
        <tbody>{成本.可下钻派生层.map(t => (
          <tr key={t.表}><td><code>{t.表}</code></td>
            <td className="num">{(t.行数 ?? 0).toLocaleString('zh')}</td></tr>
        ))}</tbody>
      </Tbl>
    </>
  )
}

/* ---------- 壳：导航结构与图标 ---------- */

const 导航组 = [
  ['总览', ['我在哪']],
  ['数据底座', ['源检查板', '数据管线']],
  ['经营专题', ['项目成本', '账龄回款', '开票纳税']],
  ['处置与追溯', ['差异工作台', '影响重跑', '审计日志']],
  ['交付与运维', ['报告中心', '排程健康', '技能']],
]
const 全部页 = 导航组.flatMap(([, xs]) => xs)

// 图标只能是无文本的 svg：E2E 用 textContent === 页名 严格比对页签，任何文字节点都会破坏它
const 线属性 = { fill: 'none', stroke: 'currentColor', strokeWidth: 1.8, strokeLinecap: 'round', strokeLinejoin: 'round' }
function 图({ d }) {
  return <svg width="15" height="15" viewBox="0 0 24 24" aria-hidden="true" focusable="false" {...线属性}><path d={d} /></svg>
}
const 图标 = {
  我在哪: <图 d="M3 11.5 12 4l9 7.5M5.5 9.8V20h13V9.8" />,
  源检查板: <图 d="M4 4h7v7H4zM13 4h7v7h-7zM4 13h7v7H4zM13 13h7v7h-7z" />,
  数据管线: <图 d="M12 3c4.4 0 8 1.3 8 3s-3.6 3-8 3-8-1.3-8-3 3.6-3 8-3zM4 6v12c0 1.7 3.6 3 8 3s8-1.3 8-3V6M4 12c0 1.7 3.6 3 8 3s8-1.3 8-3" />,
  项目成本: <图 d="M12 3a9 9 0 1 0 9 9h-9V3zM15 3.5A9 9 0 0 1 20.5 9H15V3.5z" />,
  账龄回款: <图 d="M12 3a9 9 0 1 1 0 18 9 9 0 0 1 0-18zM12 7v5l3.5 2" />,
  开票纳税: <图 d="M6 3h12v18l-2-1.4L14 21l-2-1.4L10 21l-2-1.4L6 21V3zM9 8h6M9 12h6" />,
  差异工作台: <图 d="M12 3v18M5 7h5M5 12h5M5 17h5M14 7h5M14 12h5M14 17h5" />,
  影响重跑: <图 d="M20 12a8 8 0 1 1-2.3-5.6M20 3v4h-4" />,
  排程健康: <图 d="M3 12h4l2.5-6 4 12 2.5-6h5" />,
  审计日志: <图 d="M12 3 5 6v5c0 4.5 3 8.2 7 10 4-1.8 7-5.5 7-10V6l-7-3zM9.5 12l2 2 3.5-4" />,
  报告中心: <图 d="M7 3h7l4 4v14H7V3zM14 3v4h4M10 12h5M10 16h5" />,
  技能: <图 d="M12 3l2 4.3 4.7.6-3.4 3.2.9 4.7L12 13.5l-4.2 2.3.9-4.7L5.3 7.9l4.7-.6L12 3z" />,
}

export default function App() {
  const [页, set页] = useState('我在哪')
  const [状态, set状态] = useState(null)
  const [断言, set断言] = useState(null)
  const [管线, set管线] = useState(null)
  const [技能, set技能] = useState(null)
  const [源检查, set源检查] = useState(null)
  const [我在哪数据, set我在哪] = useState(null)
  const [成本, set成本] = useState(null)
  const [账龄, set账龄] = useState(null)
  const [开票, set开票] = useState(null)
  const [工作台, set工作台] = useState(null)
  const [中心, set中心] = useState(null)
  const [影响, set影响] = useState(null)
  const [选中资产, set选中资产] = useState('')
  const [审计, set审计] = useState(null)
  const [排程, set排程] = useState(null)
  // 取不到就把失败写进状态：面板显式报错，不许无限骨架屏装加载
  const 取 = (url, set) => fetch(url)
    .then(r => { if (!r.ok) throw new Error(`HTTP ${r.status}`); return r.json() })
    .then(set).catch(e => set({ 加载失败: String(e) }))
  const 取审计 = () => 取('/api/审计日志', set审计)
  const 取影响 = (a) => 取('/api/影响重跑' + (a ? `?asset=${encodeURIComponent(a)}` : ''), set影响)
  const 取工作台 = () => 取('/api/差异工作台', set工作台)
  useEffect(() => {
    取('/api/项目成本', set成本)
    取('/api/账龄回款', set账龄)
    取('/api/开票纳税', set开票)
    取工作台()
    取('/api/报告中心', set中心)
    取影响()
    取审计()
    取('/api/排程健康', set排程)
    取('/api/状态', set状态)
    取('/api/断言', set断言)
    取('/api/数据管线', set管线)
    取('/api/技能', set技能)
    取('/api/源检查', set源检查)
    取('/api/我在哪', set我在哪)
  }, [])

  // 导航上的注意点：数据说有事，入口就亮点——不用逐页翻
  const 注意点 = {
    我在哪: (我在哪数据?.卡住的事?.length ?? 0) > 0 ? 'warn' : null,
    差异工作台: (工作台?.分组计数?.open ?? 0) > 0 ? 'warn' : null,
    排程健康: !排程 || 排程.加载失败 ? null
      : !排程.可读 ? 'warn'
      : 排程.失败数 > 0 ? 'bad'
      : 排程.仍在空跑数 > 0 ? 'warn' : null,
  }

  const 首渲 = useRef(true)
  useEffect(() => {
    if (首渲.current) { 首渲.current = false; return }
    document.querySelector('[role=tab][aria-selected=true]')?.focus()
  }, [页])
  const 键控 = e => {
    const i = 全部页.indexOf(页)
    if (e.key === 'ArrowDown' || e.key === 'ArrowRight') { e.preventDefault(); set页(全部页[(i + 1) % 全部页.length]) }
    else if (e.key === 'ArrowUp' || e.key === 'ArrowLeft') { e.preventDefault(); set页(全部页[(i - 1 + 全部页.length) % 全部页.length]) }
  }

  return (
    <div className="shell">
      <aside className="side">
        <div className="brand">
          <h1>KMFA 经营分析</h1>
          <small>经营事实一屏可核·不装健康</small>
        </div>
        {/* 页签用语义化 button+role=tab：span onClick 既不可键盘操作、也不进可访问性树，
            自动化（含 PROD.0013 Playwright）点不到——PROD.0013 真开页面时实测踩到。 */}
        <nav className="nav" role="tablist" aria-orientation="vertical" aria-label="页面导航">
          {导航组.map(([组名, 项]) => (
            <div key={组名} className="nav-group">
              <span>{组名}</span>
              {项.map(t => (
                <button key={t} type="button" role="tab" aria-selected={页 === t}
                        tabIndex={页 === t ? 0 : -1} onKeyDown={键控}
                        onClick={() => set页(t)}>{图标[t]}<span>{t}</span>{注意点[t] && <i className={`dot ${注意点[t]}`} aria-hidden="true" />}</button>
              ))}
            </div>
          ))}
        </nav>
      </aside>

      <div className="main">
        <header className="topbar">
          <h2>{页}</h2>
          {状态 && !状态.加载失败 && <>
            <span className="badge">质量 <b>{状态.页眉.质量等级}</b></span>
            <span className="badge">报告 <b>{状态.页眉.报告等级}</b></span>
            <span className={`badge${String(状态.页眉.GO状态).includes('NO_GO') ? ' risk' : ''}`}>
              <b>{状态.页眉.GO状态}</b></span>
          </>}
          {管线 && !管线.加载失败 && 管线.data_as_of_batch &&
            <span className="meta">数据截至批次 {管线.data_as_of_batch}</span>}
        </header>

        <div className="content">
          <div key={页} className="panel" role="tabpanel" aria-label={页}>
            {页 === '我在哪' && <我在哪 我在哪={我在哪数据} 断言={断言} 管线={管线} 技能={技能} />}
            {页 === '源检查板' && <源检查板 源检查={源检查} />}
            {页 === '项目成本' && <项目成本 成本={成本} />}
            {页 === '账龄回款' && <账龄回款 账龄={账龄} />}
            {页 === '开票纳税' && <开票纳税 开票={开票} />}
            {页 === '差异工作台' && <差异工作台 台={工作台} 刷新={取工作台} />}
            {页 === '报告中心' && <报告中心 中心={中心} />}
            {页 === '影响重跑' && <影响重跑 图={影响} 选中资产={选中资产}
              选资产={a => { set选中资产(a); 取影响(a) }} 刷新={取影响} />}
            {页 === '排程健康' && <排程健康 排程={排程} />}
            {页 === '审计日志' && <审计日志 审计={审计} />}
            {页 === '数据管线' && <数据管线 管线={管线} />}
            {页 === '技能' && <技能页 技能={技能} />}
          </div>
        </div>
      </div>
    </div>
  )
}
