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
    const chart = echarts.init(ref.current, null, { renderer: 'svg' })
    chart.setOption(option)
    const onResize = () => chart.resize()
    window.addEventListener('resize', onResize)
    return () => { window.removeEventListener('resize', onResize); chart.dispose() }
  }, [option])
  return <div ref={ref} style={{ width: '100%', height }} />
}

const S = {
  body: { fontFamily: '-apple-system, "PingFang SC", sans-serif', maxWidth: '64rem', margin: '0 auto', padding: '2rem' },
  header: { display: 'flex', gap: '.75rem', alignItems: 'baseline', flexWrap: 'wrap' },
  badge: { padding: '.15rem .6rem', borderRadius: 999, border: '1px solid currentColor', fontSize: '.85rem' },
  tabs: { display: 'flex', gap: '.5rem', marginTop: '1.2rem' },
  tab: on => ({ padding: '.35rem .9rem', borderRadius: '.5rem', cursor: 'pointer', border: '1px solid rgba(127,127,127,.35)', fontWeight: on ? 700 : 400, background: on ? 'rgba(127,127,127,.15)' : 'transparent' }),
  grid: { display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(14rem, 1fr))', gap: '1rem', marginTop: '1.2rem' },
  card: { border: '1px solid rgba(127,127,127,.35)', borderRadius: '.75rem', padding: '1rem' },
  num: { fontSize: '1.8rem', fontWeight: 700 },
  muted: { opacity: .65, fontSize: '.85rem' },
  td: { padding: '.35rem .45rem', borderBottom: '1px solid rgba(127,127,127,.2)', textAlign: 'left', verticalAlign: 'top' },
  select: { padding: '.25rem .5rem', borderRadius: '.4rem' },
}

function 我在哪({ 我在哪: 我, 断言, 管线, 技能 }) {
  // 三块结构与字段刻意对齐 文档/00_我在哪.md 渲染件（同源 machine/facts），验收即以其为基准
  const 状 = 我?.当前状态
  const 卡 = 我?.卡住的事 ?? []
  const 阶段 = 我?.路线图?.阶段 ?? []
  return (
    <>
      {状 && <>
        <h3 style={{ marginTop: '1rem' }}>一、当前状态</h3>
        <table style={表样}><tbody>
          <tr><td style={格样}>版本</td><td style={格样}><code>{状.版本}</code></td></tr>
          <tr><td style={格样}>进行到哪</td><td style={格样}>
            <code>{状.阶段}</code> · <code>{状.分期}</code> · <code>{状.任务}</code></td></tr>
          <tr><td style={格样}>进度</td><td style={格样}>{状.进度}</td></tr>
          <tr><td style={格样}>报告可信度</td><td style={格样}>{状.报告可信度}</td></tr>
          <tr><td style={格样}>业务结论</td><td style={格样}><b>{状.业务结论}</b></td></tr>
          <tr><td style={格样}>证据状态</td><td style={格样}>{状.证据状态}</td></tr>
          <tr><td style={格样}>卡住的事</td><td style={格样}>{状.卡住件数} 件</td></tr>
        </tbody></table>

        <h3 style={{ marginTop: '1.2rem' }}>二、卡住的事</h3>
        {卡.length === 0 ? <p style={S.muted}>无</p> : (
          <table style={表样}>
            <thead><tr>
              <th style={格样}>编号</th><th style={格样}>什么事</th>
              <th style={格样}>谁能解</th><th style={格样}>卡了多久</th>
            </tr></thead>
            <tbody>{卡.map(b => (
              <tr key={b.id}>
                <td style={格样}>{b.id}</td>
                <td style={格样}>{b.内容}</td>
                <td style={格样}>{b.owner_only ? <b>只有你能解</b> : '可代办'}</td>
                <td style={格样}>{b.首次登记}</td>
              </tr>
            ))}</tbody>
          </table>
        )}

        <h3 style={{ marginTop: '1.2rem' }}>三、路线图（{阶段.length} 阶段）</h3>
        <table style={表样}>
          <thead><tr>
            <th style={格样}>阶段</th><th style={格样}>名称</th>
            <th style={格样}>过关标准</th><th style={格样}>状态</th>
          </tr></thead>
          <tbody>{阶段.map(s => (
            <tr key={s.id}>
              <td style={格样}>{s.id}</td><td style={格样}>{s.name}</td>
              <td style={格样}>{s.gate}</td>
              <td style={{ ...格样, color: s.status === '有效' ? '#1e8449' : '#b9770e' }}>{s.status}</td>
            </tr>
          ))}</tbody>
        </table>
        <p style={S.muted}>更新于 {我.更新于}｜{我.同源}</p>
      </>}

      <h3 style={{ marginTop: '1.2rem' }}>数据面快览</h3>
      <div style={S.grid}>
        <div style={S.card}><div style={S.muted}>对账断言（closed / 总数）</div>
          <div style={S.num}>{断言 ? `${断言.closed} / ${断言.total}` : '…'}</div>
          <div style={S.muted}>{断言 ? `analyzed-open ${断言.analyzed_open}` : ''}</div></div>
        <div style={S.card}><div style={S.muted}>私有派生层数据行</div>
          <div style={S.num}>{管线 ? (管线.staging_rows_total ?? 0).toLocaleString('zh') : '…'}</div>
          <div style={S.muted}>{管线 ? `截止批次 ${管线.data_as_of_batch}` : ''}</div></div>
        <div style={S.card}><div style={S.muted}>技能</div>
          <div style={S.num}>{技能 ? 技能.count : '…'}</div>
          <div style={S.muted}>全部迁云计划中</div></div>
      </div>
      {管线?.reconciliation_status && (
        <div style={{ ...S.card, marginTop: '1rem' }}>
          <div style={S.muted}>对账现状</div>
          <div style={{ marginTop: '.4rem' }}>{管线.reconciliation_status}</div>
        </div>
      )}
      {断言?.items?.length > 0 && (
        <div style={S.grid}>
          <div style={S.card}>
            <div style={S.muted}>断言状态分布</div>
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
          <div style={S.card}>
            <div style={S.muted}>断言按域 × 状态</div>
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

function 差异工作台({ 台, 刷新 }) {
  const [分组, set分组] = useState('全部')
  const [域, set域] = useState('全部')
  const [展开, set展开] = useState(null)
  const [理由, set理由] = useState('')
  const [忙, set忙] = useState(null)
  const [提示, set提示] = useState(null)
  if (!台) return <p style={S.muted}>加载中…</p>
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
      <div style={S.grid}>
        {['open', 'closed', 'excluded'].map(g => (
          <div key={g} style={S.card}><div style={S.muted}>{g}</div>
            <div style={{ ...S.num, color: g === 'open' ? '#b9770e' : '#1e8449' }}>{台.分组计数[g]}</div></div>
        ))}
        <div style={S.card}><div style={S.muted}>决策事件</div>
          <div style={S.num}>{台.事件.总数}</div>
          <div style={S.muted}>App 写入 {台.事件['App 写入']}｜已冲正 {台.事件.已被冲正}</div></div>
      </div>

      <div style={{ ...S.card, marginTop: '1rem', borderLeft: '4px solid #1e8449' }}>
        <b>写入纪律</b>
        <div style={{ ...S.muted, marginTop: '.3rem' }}>
          append-only：{台.写入纪律.append_only ? '是' : '否'}｜允许静默改写：{台.写入纪律['允许静默改写'] ? '是' : '否'}｜
          断言表可写：{台.写入纪律['断言表可写'] ? '是' : '否'}
        </div>
        <div style={{ ...S.muted, marginTop: '.2rem' }}>改主意的做法：{台.写入纪律['改主意的做法']}</div>
        <div style={{ ...S.muted, marginTop: '.2rem' }}>
          双向一致：本台孤儿事件 {台.双向一致.本台孤儿事件数} 条 → {台.双向一致.一致 ? '一致 ✅' : '不一致 ⚠️'}
          ｜仓内未挂载 {台.双向一致.仓内未挂载事件数} 条（指向治理记录号，非断言号）
        </div>
      </div>

      <div style={{ display: 'flex', gap: '.8rem', alignItems: 'center', marginTop: '1rem', flexWrap: 'wrap' }}>
        <span style={S.muted}>分组</span>
        <select style={S.select} value={分组} onChange={e => set分组(e.target.value)}>
          {['全部', 'open', 'closed', 'excluded'].map(d => <option key={d}>{d}</option>)}</select>
        <span style={S.muted}>域</span>
        <select style={S.select} value={域} onChange={e => set域(e.target.value)}>
          {域列表.map(d => <option key={d}>{d}</option>)}</select>
        <span style={S.muted}>{rows.length} 条</span>
      </div>

      <table style={表样}>
        <thead><tr>
          <th style={格样}>断言</th><th style={格样}>口径</th><th style={格样}>期间</th>
          <th style={格样}>差异（元）</th><th style={格样}>分组</th><th style={格样}>现行决策</th>
        </tr></thead>
        <tbody>{rows.map(it => (
          <React.Fragment key={it.断言}>
            <tr onClick={() => { set展开(展开 === it.断言 ? null : it.断言); set提示(null) }}
                style={{ cursor: 'pointer' }}>
              <td style={格样}><code>{it.断言}</code></td>
              <td style={格样}>{it.口径}</td>
              <td style={格样}>{it.期间}</td>
              <td style={格样}>{it.差异元 === null ? '—' : `¥${it.差异元}`}</td>
              <td style={{ ...格样, color: it.分组 === 'open' ? '#b9770e' : '#1e8449' }}>{it.分组}</td>
              <td style={格样}>{it.现行决策
                ? <span><b>{it.现行决策.决策}</b> → {it.现行决策.到状态}</span>
                : <span style={S.muted}>未决策</span>}</td>
            </tr>
            {展开 === it.断言 && (
              <tr><td style={格样} colSpan={6}>
                <div style={{ marginBottom: '.5rem' }}>{it.结论 ?? '（无 finding）'}</div>
                <div style={{ display: 'flex', gap: '.5rem', alignItems: 'center', flexWrap: 'wrap' }}>
                  <input style={{ ...S.select, flex: '1 1 22rem', minWidth: '14rem' }}
                         placeholder="决策理由（必填，会连同事件一起留痕）"
                         value={理由} onChange={e => set理由(e.target.value)} />
                  {台.决策入口.map(d => (
                    <button key={d.决策} type="button" disabled={忙 !== null}
                            style={{ ...S.tab(false), font: 'inherit', cursor: 'pointer' }}
                            onClick={() => 提交('/api/差异工作台/决策',
                              { 断言: it.断言, 决策: d.决策 }, `${it.断言}-${d.决策}`)}>
                      {忙 === `${it.断言}-${d.决策}` ? '写入中…' : `${d.决策} → ${d.到状态}`}
                    </button>
                  ))}
                </div>
                {提示 && (
                  <div style={{ marginTop: '.5rem', color: 提示.好 ? '#1e8449' : '#c0392b' }}>{提示.文}</div>
                )}
                {it.决策事件.length > 0 && (
                  <table style={表样}>
                    <thead><tr>
                      <th style={格样}>事件号</th><th style={格样}>决策</th><th style={格样}>理由</th>
                      <th style={格样}>时间</th><th style={格样}>来源</th><th style={格样}>操作</th>
                    </tr></thead>
                    <tbody>{it.决策事件.map(e => (
                      <tr key={e.事件号} style={{ opacity: e.已被冲正 ? .5 : 1 }}>
                        <td style={格样}><code>{e.事件号}</code></td>
                        <td style={格样}>{e.决策 ?? e.动作}{e.已被冲正 && ' （已冲正）'}
                          {e.冲正的是 && <span style={S.muted}> 冲正 {e.冲正的是}</span>}</td>
                        <td style={格样}>{e.理由}</td>
                        <td style={格样}>{e.时间}</td>
                        <td style={格样}>{e.来源}</td>
                        <td style={格样}>{(!e.已被冲正 && !e.冲正的是 && e.来源 !== '仓内治理面（只读）') ? (
                          <button type="button" disabled={忙 !== null}
                                  style={{ ...S.tab(false), font: 'inherit', cursor: 'pointer' }}
                                  onClick={() => 提交('/api/差异工作台/冲正',
                                    { 冲正事件号: e.事件号 }, `rev-${e.事件号}`)}>
                            {忙 === `rev-${e.事件号}` ? '写入中…' : '冲正'}
                          </button>) : <span style={S.muted}>—</span>}</td>
                      </tr>
                    ))}</tbody>
                  </table>
                )}
              </td></tr>
            )}
          </React.Fragment>
        ))}</tbody>
      </table>
    </>
  )
}

function 报告中心({ 中心 }) {
  if (!中心) return <p style={S.muted}>加载中…</p>
  const 水 = 中心.水印, 判 = 中心.交付判据
  return (
    <>
      <div style={S.grid}>
        <div style={S.card}><div style={S.muted}>报告等级</div>
          <div style={{ ...S.num, color: '#c0392b' }}>{中心.页眉.报告等级}</div></div>
        <div style={S.card}><div style={S.muted}>质量等级</div>
          <div style={S.num}>{中心.页眉.质量等级}</div></div>
        <div style={S.card}><div style={S.muted}>delivery 状态</div>
          <div style={{ ...S.num, fontSize: '1.2rem', color: 判.delivery_allowed ? '#1e8449' : '#c0392b' }}>
            {中心.页眉.delivery状态}</div></div>
        <div style={S.card}><div style={S.muted}>导出登记</div>
          <div style={S.num}>{中心.导出登记.条数}</div>
          <div style={S.muted}>追加式，不可改写</div></div>
      </div>

      <div style={{ ...S.card, marginTop: '1rem', borderLeft: '4px solid #c0392b' }}>
        <b>水印：{水.生效中 ? '生效中，且无法关闭' : '已解除'}</b>
        {水.文案 && <div style={{ marginTop: '.3rem', fontFamily: 'ui-monospace, monospace' }}>{水.文案}</div>}
        <div style={{ ...S.muted, marginTop: '.3rem' }}>
          覆盖格式：{水.覆盖格式.join(' / ')}｜可关闭：{水.可关闭 ? '是' : '否'}
        </div>
        <div style={{ ...S.muted, marginTop: '.2rem' }}>去除条件：{水.去除条件}</div>
      </div>

      <h3 style={{ marginTop: '1.2rem' }}>八份报告 × 三格式</h3>
      <table style={表样}>
        <thead><tr>
          <th style={格样}>号</th><th style={格样}>标题</th><th style={格样}>正文字数</th>
          <th style={格样}>下载</th>
        </tr></thead>
        <tbody>{中心.报告.map(r => (
          <tr key={r.编号}>
            <td style={格样}>{r.编号}</td>
            <td style={格样}>{r.标题}</td>
            <td style={格样}>{r.正文字数.toLocaleString('zh')}</td>
            <td style={格样}>{r.格式.map(f => (
              <a key={f.格式} href={f.下载} style={{ marginRight: '.7rem' }}
                 title={f.可提交公开仓 ? '公开安全，可提交' : '仅运行时生成，不入公开仓'}>
                {f.格式.toUpperCase()}{f.可提交公开仓 ? '' : '（运行时）'}
              </a>
            ))}</td>
          </tr>
        ))}</tbody>
      </table>

      <h3 style={{ marginTop: '1.2rem' }}>PDF 策略</h3>
      <div style={{ ...S.card, borderLeft: '4px solid #b9770e' }}>
        <div>{中心.PDF策略.说明}</div>
        <div style={{ ...S.muted, marginTop: '.3rem' }}>中文渲染：{中心.PDF策略.中文渲染}</div>
      </div>

      {中心.导出登记.记录.length > 0 && (
        <>
          <h3 style={{ marginTop: '1.2rem' }}>导出 hash 登记（最近 {中心.导出登记.记录.length} 条）</h3>
          <table style={表样}>
            <thead><tr>
              <th style={格样}>号</th><th style={格样}>格式</th><th style={格样}>sha256</th>
              <th style={格样}>字节</th><th style={格样}>水印</th><th style={格样}>时间</th>
            </tr></thead>
            <tbody>{中心.导出登记.记录.slice().reverse().map((e, i) => (
              <tr key={i}>
                <td style={格样}>{e.报告}</td>
                <td style={格样}>{e.格式.toUpperCase()}</td>
                <td style={格样}><code style={{ fontSize: '.72rem' }}>{String(e.sha256).slice(7, 27)}…</code></td>
                <td style={格样}>{(e.字节 ?? 0).toLocaleString('zh')}</td>
                <td style={{ ...格样, color: e.水印已加 ? '#c0392b' : '#1e8449' }}>
                  {e.水印已加 ? '已加' : '无'}</td>
                <td style={格样}>{e.导出时间}</td>
              </tr>
            ))}</tbody>
          </table>
        </>
      )}
    </>
  )
}

function 数据管线({ 管线 }) {
  if (!管线) return <div style={{ ...S.card, marginTop: '1.2rem' }}>加载中…</div>
  const 表 = Object.entries(管线.staging_tables ?? {}).sort((a, b) => (b[1].rows ?? 0) - (a[1].rows ?? 0))
  return (
    <>
      <div style={S.grid}>
        <div style={S.card}><div style={S.muted}>接入原始文件</div>
          <div style={S.num}>{管线.raw_assets_registered ?? '—'}</div>
          <div style={S.muted}>内容寻址入仓（KMDatabase/data）</div></div>
        <div style={S.card}><div style={S.muted}>派生层数据行</div>
          <div style={S.num}>{(管线.staging_rows_total ?? 0).toLocaleString('zh')}</div>
          <div style={S.muted}>截止批次 {管线.data_as_of_batch}</div></div>
        <div style={S.card}><div style={S.muted}>质量档位</div>
          <div style={{ fontSize: '1.05rem', fontWeight: 700, marginTop: '.3rem' }}>{管线.quality_grade_current ?? '—'}</div>
          <div style={S.muted}>未决质量卡点 {管线.quality_blockers_open ?? 0} 项</div></div>
      </div>
      <div style={{ ...S.card, marginTop: '1rem' }}>
        <div style={S.muted}>派生层各表行数（对数轴）</div>
        <Chart height={`${Math.max(表.length * 1.7, 10)}rem`} option={{
          tooltip: {}, grid: { left: 8, right: 48, top: 8, bottom: 8, containLabel: true },
          xAxis: { type: 'log', minorSplitLine: { show: false } },
          yAxis: { type: 'category', data: 表.map(([名]) => 名).reverse(), axisLabel: { fontSize: 10 } },
          series: [{ type: 'bar', data: 表.map(([, 值]) => 值.rows ?? 0).reverse(),
            label: { show: true, position: 'right', formatter: p => p.value.toLocaleString('zh') } }],
        }} />
      </div>
      <div style={{ ...S.card, marginTop: '1rem' }}>
        <div style={S.muted}>派生层各表（私有 DuckDB，可由工具链零重建）</div>
        <table style={{ width: '100%', borderCollapse: 'collapse', marginTop: '.6rem', fontSize: '.85rem' }}>
          <thead><tr><th style={S.td}>表</th><th style={{ ...S.td, textAlign: 'right' }}>行数</th></tr></thead>
          <tbody>
            {表.map(([名, 值]) => (
              <tr key={名}><td style={S.td}>{名}</td>
                <td style={{ ...S.td, textAlign: 'right' }}>{(值.rows ?? 0).toLocaleString('zh')}</td></tr>
            ))}
          </tbody>
        </table>
      </div>
      {管线.reconciliation_status && (
        <div style={{ ...S.card, marginTop: '1rem' }}>
          <div style={S.muted}>对账现状</div>
          <div style={{ marginTop: '.4rem' }}>{管线.reconciliation_status}</div>
        </div>
      )}
      {Array.isArray(管线.next_gates) && 管线.next_gates.length > 0 && (
        <div style={{ ...S.card, marginTop: '1rem' }}>
          <div style={S.muted}>下一步门禁</div>
          <ul style={{ margin: '.4rem 0 0 1.1rem', padding: 0 }}>
            {管线.next_gates.map((g, i) => <li key={i} style={{ marginTop: '.2rem' }}>{typeof g === 'string' ? g : JSON.stringify(g)}</li>)}
          </ul>
        </div>
      )}
      <div style={{ ...S.muted, marginTop: '.8rem' }}>血缘：{管线.lineage ?? '—'}</div>
    </>
  )
}

function 技能页({ 技能 }) {
  const [展开, set展开] = useState(null)
  if (!技能) return <div style={{ ...S.card, marginTop: '1.2rem' }}>加载中…</div>
  const rows = 技能.skills ?? []
  return (
    <>
      <div style={{ ...S.card, marginTop: '1.2rem' }}>
        <div style={S.muted}>运行策略</div>
        <div style={{ marginTop: '.4rem' }}>
          全部 {技能.count} 项技能依赖云端运行（Oracle 基座 <code>KMFA/deploy/skills-runtime/</code>）；
          本机不常驻。等待实例开通后按运行手册上云，测试收发对象「张霖泽」。
        </div>
      </div>
      <div style={{ ...S.card, marginTop: '1rem' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '.85rem' }}>
          <thead><tr><th style={S.td}>技能</th><th style={S.td}>排程</th><th style={S.td}>外部依赖</th><th style={S.td}>迁移待办</th></tr></thead>
          <tbody>
            {rows.map(it => (
              <React.Fragment key={it.id}>
                <tr onClick={() => set展开(展开 === it.id ? null : it.id)} style={{ cursor: 'pointer' }}>
                  <td style={S.td}>{it.名称 ?? it.id}</td>
                  <td style={S.td}>{(it.排程 ?? []).length ? it.排程.join('、') : '—'}</td>
                  <td style={S.td}>{(it.外部依赖 ?? []).length ? it.外部依赖.join('、') : '—'}</td>
                  <td style={S.td}>{it.本地路径硬编码 > 0 ? `本地路径硬编码 ${it.本地路径硬编码} 处` : '无'}</td>
                </tr>
                {展开 === it.id && (
                  <tr><td style={{ ...S.td, opacity: .8 }} colSpan={4}>
                    <div>{it.用途 ?? '（登记表无用途描述）'}</div>
                    <div style={S.muted}>机器 id：{it.id}｜登记状态：{it.登记状态 ?? '—'}</div>
                  </td></tr>
                )}
              </React.Fragment>
            ))}
          </tbody>
        </table>
      </div>
    </>
  )
}

const 表样 = { width: '100%', borderCollapse: 'collapse', marginTop: '.6rem', fontSize: '.85rem' }
const 格样 = { border: '1px solid rgba(127,127,127,.3)', padding: '.35rem .5rem', textAlign: 'left' }

function 源检查板({ 源检查 }) {
  if (!源检查) return <p style={S.muted}>加载中…</p>
  const 协议 = 源检查.矩阵协议, 覆盖 = 源检查.覆盖矩阵, 鲜 = 源检查.新鲜度, 派生 = 源检查.派生层
  return (
    <>
      <div style={{ display: 'flex', gap: '.8rem', flexWrap: 'wrap', marginTop: '1rem' }}>
        <div style={S.card}><div style={S.muted}>登记资产</div><div style={S.num}>{覆盖.资产合计}</div></div>
        <div style={S.card}><div style={S.muted}>数据批次</div><div style={S.num}>{鲜.数据批次 || '—'}</div></div>
        <div style={S.card}><div style={S.muted}>派生表 / 行</div>
          <div style={S.num}>{派生.表数} / {(派生.行合计 ?? 0).toLocaleString('zh')}</div></div>
        <div style={S.card}><div style={S.muted}>新鲜度</div>
          <div style={{ ...S.num, color: 鲜.stale ? '#c0392b' : '#1e8449' }}>{鲜.stale ? 'STALE' : 'FRESH'}</div></div>
      </div>
      <p style={S.muted}>{鲜.提示}｜血缘批次：{(鲜.血缘批次 || []).join('、') || '—'}</p>

      <h3 style={{ marginTop: '1.2rem' }}>源 × 登记状态 矩阵</h3>
      <table style={表样}>
        <thead>
          <tr>
            <th style={格样}>源</th>
            {覆盖.状态列.map(s => <th key={s} style={格样}>{s}</th>)}
            <th style={格样}>合计</th>
          </tr>
        </thead>
        <tbody>
          {覆盖.行.map(r => (
            <tr key={r.源}>
              <td style={格样}>{r.源}</td>
              {覆盖.状态列.map(s => <td key={s} style={格样}>{r[s] ?? 0}</td>)}
              <td style={{ ...格样, fontWeight: 700 }}>{r.合计}</td>
            </tr>
          ))}
        </tbody>
      </table>

      <h3 style={{ marginTop: '1.2rem' }}>正式源检查矩阵（协议态）</h3>
      <table style={表样}>
        <tbody>
          <tr><td style={格样}>schema</td><td style={格样}>{协议.schema || '—'}</td></tr>
          <tr><td style={格样}>阶段</td><td style={格样}>{协议.阶段 || '—'}</td></tr>
          <tr><td style={格样}>状态</td><td style={格样}>{协议.状态 || '—'}</td></tr>
          <tr><td style={格样}>已提交源行</td>
            <td style={{ ...格样, fontWeight: 700, color: 协议.已提交源行 ? 'inherit' : '#b9770e' }}>{协议.已提交源行}</td></tr>
          <tr><td style={格样}>必需维度</td><td style={格样}>{(协议.必需维度 || []).join('、')}</td></tr>
          <tr><td style={格样}>允许状态</td><td style={格样}>{(协议.允许状态 || []).join('、')}</td></tr>
        </tbody>
      </table>
      <p style={S.muted}>{协议.说明}</p>
    </>
  )
}

function 账龄回款({ 账龄 }) {
  if (!账龄) return <p style={S.muted}>加载中…</p>
  const 对 = 账龄.回款对账, 恒 = 账龄.账龄恒等式, 构 = 账龄.账龄结构层
  return (
    <>
      <div style={S.grid}>
        <div style={S.card}><div style={S.muted}>回款对账月数</div><div style={S.num}>{对.月数}</div></div>
        <div style={S.card}><div style={S.muted}>零分差月数</div>
          <div style={{ ...S.num, color: '#1e8449' }}>{对.零分差月数}</div></div>
        <div style={S.card}><div style={S.muted}>未闭月数</div>
          <div style={{ ...S.num, color: 对.未闭月数 ? '#b9770e' : '#1e8449' }}>{对.未闭月数}</div></div>
        <div style={S.card}><div style={S.muted}>最大差异</div>
          <div style={S.num}>{对.最大差异 ? `¥${对.最大差异.差异元}` : '—'}</div>
          <div style={S.muted}>{对.最大差异?.期间 ?? ''}</div></div>
      </div>

      <h3 style={{ marginTop: '1.2rem' }}>回款逐月对账（真实分差）</h3>
      <table style={表样}>
        <thead><tr>
          <th style={格样}>断言</th><th style={格样}>口径</th><th style={格样}>期间</th>
          <th style={格样}>差异（元）</th><th style={格样}>差异（分）</th><th style={格样}>状态</th>
        </tr></thead>
        <tbody>{对.逐月.map(m => (
          <tr key={m.断言}>
            <td style={格样}><code>{m.断言}</code></td>
            <td style={格样}>{m.口径}</td>
            <td style={格样}>{m.期间}</td>
            <td style={{ ...格样, fontWeight: m.差异分 ? 700 : 400,
                          color: m.差异分 ? '#b9770e' : '#1e8449' }}>
              {m.差异元 === null ? '—' : `¥${m.差异元}`}</td>
            <td style={格样}>{m.差异分 ?? '—'}</td>
            <td style={{ ...格样, color: m.状态 === 'analyzed_open' ? '#b9770e' : '#1e8449' }}>{m.状态}</td>
          </tr>
        ))}</tbody>
      </table>

      <h3 style={{ marginTop: '1.2rem' }}>账龄恒等式</h3>
      <table style={表样}>
        <thead><tr><th style={格样}>断言</th><th style={格样}>口径</th><th style={格样}>快照</th>
          <th style={格样}>差异分</th><th style={格样}>状态</th></tr></thead>
        <tbody>{恒.map(r => (
          <tr key={r.断言}>
            <td style={格样}><code>{r.断言}</code></td><td style={格样}>{r.口径}</td>
            <td style={格样}>{r.快照}</td>
            <td style={{ ...格样, color: r.差异分 === 0 ? '#1e8449' : '#b9770e' }}>{r.差异分}</td>
            <td style={格样}>{r.状态}</td>
          </tr>
        ))}</tbody>
      </table>

      <h3 style={{ marginTop: '1.2rem' }}>账龄结构层（值仍被阻断）</h3>
      <div style={{ ...S.card, borderLeft: '4px solid #b9770e' }}>
        <div>{账龄.诚实边界}</div>
        <div style={{ ...S.muted, marginTop: '.4rem' }}>
          源泳道 {构.源泳道数} 条，状态 <code>{构.泳道数据状态.join('、')}</code>；
          优先事项 {构.优先事项数} 条（匿名指针）；允许作经营依据：{构.允许作经营依据 ? '是' : '否'}
        </div>
      </div>
      <ul style={{ ...S.muted, marginTop: '.6rem' }}>{构.限制.map((t, i) => <li key={i}>{t}</li>)}</ul>

      <h3 style={{ marginTop: '1.2rem' }}>派生层规模</h3>
      <table style={表样}>
        <thead><tr><th style={格样}>staging 表</th><th style={格样}>真实行数</th></tr></thead>
        <tbody>{账龄.派生层规模.map(t => (
          <tr key={t.表}><td style={格样}><code>{t.表}</code></td>
            <td style={格样}>{(t.行数 ?? 0).toLocaleString('zh')}</td></tr>
        ))}</tbody>
      </table>
    </>
  )
}

function 断言表({ 块, 标题 }) {
  return (
    <>
      <h3 style={{ marginTop: '1.2rem' }}>{标题}（真实分差 {块.条数} 条）</h3>
      <table style={表样}>
        <thead><tr>
          <th style={格样}>断言</th><th style={格样}>口径</th><th style={格样}>期间</th>
          <th style={格样}>差异（元）</th><th style={格样}>差异（分）</th><th style={格样}>状态</th>
        </tr></thead>
        <tbody>{块.逐条.map(r => (
          <tr key={r.断言}>
            <td style={格样}><code>{r.断言}</code></td>
            <td style={格样}>{r.口径}</td>
            <td style={格样}>{r.期间}</td>
            <td style={{ ...格样, fontWeight: r.差异分 ? 700 : 400,
                          color: r.差异分 ? '#b9770e' : '#1e8449' }}>
              {r.差异元 === null ? '—' : `¥${r.差异元}`}</td>
            <td style={格样}>{r.差异分 ?? '—'}</td>
            <td style={{ ...格样, color: r.状态 === 'analyzed_open' ? '#b9770e' : '#1e8449' }}>{r.状态}</td>
          </tr>
        ))}</tbody>
      </table>
      {块.逐条.filter(r => r.结论).map(r => (
        <details key={r.断言} style={{ ...S.muted, marginTop: '.4rem' }}>
          <summary><code>{r.断言}</code> 结论</summary>
          <div style={{ marginTop: '.3rem', lineHeight: 1.5 }}>{r.结论}</div>
        </details>
      ))}
    </>
  )
}

function 开票纳税({ 开票 }) {
  if (!开票) return <p style={S.muted}>加载中…</p>
  const 红 = 开票.红线, 构 = 开票.结构层, 政 = 开票.税务政策证据
  const 红线项 = Object.entries(红)
  const 红线全零 = 红线项.every(([, v]) => v === 0)
  const 全部方法 = Object.entries(构).flatMap(([组, v]) => (v.方法 || []).map(m => ({ ...m, 组 })))
  return (
    <>
      <div style={S.grid}>
        <div style={S.card}><div style={S.muted}>开票域断言</div>
          <div style={S.num}>{开票.开票对账.条数}</div>
          <div style={S.muted}>未闭 {开票.开票对账.未闭条数}</div></div>
        <div style={S.card}><div style={S.muted}>税务域断言</div>
          <div style={S.num}>{开票.税务对账.条数}</div>
          <div style={S.muted}>未闭 {开票.税务对账.未闭条数}</div></div>
        <div style={S.card}><div style={S.muted}>贷款域断言</div>
          <div style={S.num}>{开票.贷款对账.条数}</div>
          <div style={{ ...S.muted, color: '#1e8449' }}>零分差 {开票.贷款对账.零分差条数}</div></div>
        <div style={S.card}><div style={S.muted}>红线动作合计</div>
          <div style={{ ...S.num, color: 红线全零 ? '#1e8449' : '#c0392b' }}>
            {红线项.reduce((a, [, v]) => a + (v ?? 0), 0)}</div>
          <div style={S.muted}>不开票·不申报·不动账</div></div>
      </div>

      <断言表 块={开票.开票对账} 标题="开票对账" />
      <断言表 块={开票.税务对账} 标题="税务对账" />
      <断言表 块={开票.贷款对账} 标题="贷款对账" />

      <h3 style={{ marginTop: '1.2rem' }}>红线：本页只读，不产生任何业务动作</h3>
      <table style={表样}>
        <thead><tr><th style={格样}>动作</th><th style={格样}>事实计数</th></tr></thead>
        <tbody>{红线项.map(([k, v]) => (
          <tr key={k}><td style={格样}>{k}</td>
            <td style={{ ...格样, color: v === 0 ? '#1e8449' : '#c0392b', fontWeight: 700 }}>{v}</td></tr>
        ))}</tbody>
      </table>

      <h3 style={{ marginTop: '1.2rem' }}>计划层（值仍被阻断，故不出计划金额）</h3>
      <div style={{ ...S.card, borderLeft: '4px solid #b9770e' }}>
        <div>{开票.诚实边界}</div>
      </div>
      <table style={表样}>
        <thead><tr><th style={格样}>计划段</th><th style={格样}>决策</th>
          <th style={格样}>已证值绑定车道</th><th style={格样}>公开业务金额</th>
          <th style={格样}>车道</th></tr></thead>
        <tbody>{Object.entries(构).map(([名, v]) => (
          <tr key={名}>
            <td style={格样}>{名}</td>
            <td style={{ ...格样, color: '#b9770e' }}>{v.决策}</td>
            <td style={格样}>{v.已证值绑定车道数}</td>
            <td style={格样}>{v.公开业务金额数}</td>
            <td style={格样}>{(v.车道 || []).map(l => l.车道).join('、')}</td>
          </tr>
        ))}</tbody>
      </table>

      <h4 style={{ marginTop: '1rem' }}>九个方法的阻断原因（定义已完备，缺权威值绑定）</h4>
      <table style={表样}>
        <thead><tr><th style={格样}>方法</th><th style={格样}>定义完备</th>
          <th style={格样}>产出状态</th><th style={格样}>依赖车道</th>
          <th style={格样}>还缺什么</th></tr></thead>
        <tbody>{全部方法.map(m => (
          <tr key={`${m.组}-${m.方法}`}>
            <td style={格样}>{m.名称 ?? m.方法}<br />
              <code style={{ fontSize: '.75rem', opacity: .65 }}>{m.方法}</code></td>
            <td style={{ ...格样, color: m.定义完备 ? '#1e8449' : '#b9770e' }}>
              {m.定义完备 ? '是' : '否'}</td>
            <td style={{ ...格样, color: '#b9770e' }}>{m.产出状态}</td>
            {/* 相邻 <code> 之间要有真实空白节点：只靠 margin 时 innerText/复制会粘连成一个词 */}
            <td style={格样}>{(m.依赖车道 || []).map((l, i) => (
              <React.Fragment key={l}>{i > 0 && ' '}<code>{l}</code></React.Fragment>))}</td>
            <td style={格样}>{m.说明}</td>
          </tr>
        ))}</tbody>
      </table>

      <h3 style={{ marginTop: '1.2rem' }}>
        税务政策：证据缺口与风险提示（{政.证据完备项目数}/{政.项目数} 证据完备，不作资格判断）
      </h3>
      <table style={表样}>
        <thead><tr><th style={格样}>项目</th><th style={格样}>风险等级</th>
          <th style={格样}>风险提示</th><th style={格样}>证据缺口</th></tr></thead>
        <tbody>{政.逐项.map(p => (
          <tr key={p.项目}>
            <td style={格样}>{p.项目}</td>
            <td style={{ ...格样, color: p.风险等级 === 'high' ? '#c0392b' : '#b9770e' }}>{p.风险等级}</td>
            <td style={格样}>{p.风险提示}</td>
            <td style={格样}>{p.证据缺口}</td>
          </tr>
        ))}</tbody>
      </table>

      <h3 style={{ marginTop: '1.2rem' }}>派生层规模</h3>
      <table style={表样}>
        <thead><tr><th style={格样}>staging 表</th><th style={格样}>真实行数</th></tr></thead>
        <tbody>{开票.派生层规模.map(t => (
          <tr key={t.表}><td style={格样}><code>{t.表}</code></td>
            <td style={格样}>{(t.行数 ?? 0).toLocaleString('zh')}</td></tr>
        ))}</tbody>
      </table>
    </>
  )
}

function 项目成本({ 成本 }) {
  if (!成本) return <p style={S.muted}>加载中…</p>
  const 层 = 成本.事实层, 构 = 成本.必需结构, 阻 = 成本.阻塞链
  const 阻塞中 = 层.已算金额记录数 === 0
  return (
    <>
      {阻塞中 && (
        <div style={{ ...S.card, marginTop: '1rem', borderLeft: '4px solid #b9770e' }}>
          <b>金额尚不可计算——本页不产出任何毛利数字</b>
          <div style={{ marginTop: '.4rem' }}>{成本.诚实边界}</div>
        </div>
      )}
      <div style={S.grid}>
        <div style={S.card}><div style={S.muted}>事实层记录</div><div style={S.num}>{层.记录数}</div>
          <div style={S.muted}>已算金额 {层.已算金额记录数}</div></div>
        <div style={S.card}><div style={S.muted}>成本类别槽位</div><div style={S.num}>{构.成本类别.length}</div></div>
        <div style={S.card}><div style={S.muted}>事实指标槽位</div><div style={S.num}>{构.事实指标.length}</div></div>
      </div>
      <p style={S.muted}>状态 <code>{层.状态}</code>｜公式 {层.公式版本}｜映射 {层.映射版本}｜生成于 {层.生成于}</p>

      <h3 style={{ marginTop: '1.2rem' }}>成本类别 × 事实指标（结构骨架）</h3>
      <p style={S.muted}>成本类别：{构.成本类别.join('、')}</p>
      <p style={S.muted}>事实指标：{构.事实指标.join('、')}</p>

      <h3 style={{ marginTop: '1.2rem' }}>事实记录</h3>
      <table style={表样}>
        <thead><tr>
          <th style={格样}>记录号</th><th style={格样}>项目实体</th><th style={格样}>计算状态</th>
          <th style={格样}>金额已计算</th><th style={格样}>成本/指标槽位</th><th style={格样}>已登记哈希</th>
          <th style={格样}>明文已公开</th>
        </tr></thead>
        <tbody>{成本.记录.map(r => (
          <tr key={r.记录号}>
            <td style={格样}><code>{r.记录号}</code></td>
            <td style={格样}><code>{r.项目实体}</code></td>
            <td style={{ ...格样, color: '#b9770e' }}>{r.计算状态}</td>
            <td style={格样}>{r.金额已计算 ? '是' : '否'}</td>
            <td style={格样}>{r.成本槽位} / {r.指标槽位}</td>
            <td style={格样}>{r.已登记哈希}</td>
            <td style={格样}>{r.明文已公开 ? '是' : '否（仅私有面）'}</td>
          </tr>
        ))}</tbody>
      </table>

      <h3 style={{ marginTop: '1.2rem' }}>阻塞链</h3>
      <p style={S.muted}>{阻.直接原因}｜基准 <code>{阻.基准引用}</code></p>
      <table style={表样}>
        <thead><tr><th style={格样}>编号</th><th style={格样}>根阻塞</th><th style={格样}>谁能解</th><th style={格样}>已卡</th></tr></thead>
        <tbody>{阻.根阻塞.map(b => (
          <tr key={b.编号}>
            <td style={格样}>{b.编号}</td><td style={格样}>{b.内容}</td>
            <td style={格样}>{b.只有Owner可解 ? <b>只有你能解</b> : '可代办'}</td>
            <td style={格样}>{b.已卡}</td>
          </tr>
        ))}</tbody>
      </table>

      <h3 style={{ marginTop: '1.2rem' }}>可下钻派生层（A0 就位后据此归集）</h3>
      <table style={表样}>
        <thead><tr><th style={格样}>staging 表</th><th style={格样}>真实行数</th></tr></thead>
        <tbody>{成本.可下钻派生层.map(t => (
          <tr key={t.表}><td style={格样}><code>{t.表}</code></td>
            <td style={格样}>{(t.行数 ?? 0).toLocaleString('zh')}</td></tr>
        ))}</tbody>
      </table>
    </>
  )
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
  const 取工作台 = () => fetch('/api/差异工作台').then(r => r.json()).then(set工作台)
  useEffect(() => {
    fetch('/api/项目成本').then(r => r.json()).then(set成本)
    fetch('/api/账龄回款').then(r => r.json()).then(set账龄)
    fetch('/api/开票纳税').then(r => r.json()).then(set开票)
    取工作台()
    fetch('/api/报告中心').then(r => r.json()).then(set中心)
    fetch('/api/状态').then(r => r.json()).then(set状态)
    fetch('/api/断言').then(r => r.json()).then(set断言)
    fetch('/api/数据管线').then(r => r.json()).then(set管线)
    fetch('/api/技能').then(r => r.json()).then(set技能)
    fetch('/api/源检查').then(r => r.json()).then(set源检查)
    fetch('/api/我在哪').then(r => r.json()).then(set我在哪)
  }, [])
  return (
    <div style={S.body}>
      <header style={S.header}>
        <h1 style={{ fontSize: '1.4rem', margin: 0 }}>KMFA 经营分析</h1>
        {状态 && <>
          <span style={S.badge}>质量 {状态.页眉.质量等级}</span>
          <span style={S.badge}>报告 {状态.页眉.报告等级}</span>
          <span style={S.badge}>{状态.页眉.GO状态}</span>
        </>}
      </header>
      <nav style={S.tabs}>
        {/* 页签用语义化 button+role=tab：span onClick 既不可键盘操作、也不进可访问性树，
            自动化（含 PROD.0013 Playwright）点不到——本单元真开页面时实测踩到。 */}
        {['我在哪', '源检查板', '项目成本', '账龄回款', '开票纳税', '差异工作台', '报告中心', '数据管线', '技能'].map(t => (
          <button key={t} type="button" role="tab" aria-selected={页 === t}
                  style={{ ...S.tab(页 === t), font: 'inherit' }} onClick={() => set页(t)}>{t}</button>
        ))}
      </nav>
      {页 === '我在哪' && <我在哪 我在哪={我在哪数据} 断言={断言} 管线={管线} 技能={技能} />}
      {页 === '源检查板' && <源检查板 源检查={源检查} />}
      {页 === '项目成本' && <项目成本 成本={成本} />}
      {页 === '账龄回款' && <账龄回款 账龄={账龄} />}
      {页 === '开票纳税' && <开票纳税 开票={开票} />}
      {页 === '差异工作台' && <差异工作台 台={工作台} 刷新={取工作台} />}
      {页 === '报告中心' && <报告中心 中心={中心} />}
      {页 === '数据管线' && <数据管线 管线={管线} />}
      {页 === '技能' && <技能页 技能={技能} />}
    </div>
  )
}
