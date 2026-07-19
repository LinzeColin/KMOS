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

function 差异工作台({ 断言 }) {
  const [域, set域] = useState('全部')
  const [态, set态] = useState('全部')
  const [展开, set展开] = useState(null)
  const items = 断言?.items ?? []
  const 域列表 = useMemo(() => ['全部', ...new Set(items.map(i => i.domain).filter(Boolean))], [items])
  const 态列表 = useMemo(() => ['全部', ...new Set(items.map(i => i.status).filter(Boolean))], [items])
  const rows = items.filter(i => (域 === '全部' || i.domain === 域) && (态 === '全部' || i.status === 态))
  return (
    <div style={{ ...S.card, marginTop: '1.2rem' }}>
      <div style={{ display: 'flex', gap: '.8rem', alignItems: 'center' }}>
        <span style={S.muted}>域</span>
        <select style={S.select} value={域} onChange={e => set域(e.target.value)}>{域列表.map(d => <option key={d}>{d}</option>)}</select>
        <span style={S.muted}>状态</span>
        <select style={S.select} value={态} onChange={e => set态(e.target.value)}>{态列表.map(d => <option key={d}>{d}</option>)}</select>
        <span style={S.muted}>{rows.length} 条</span>
      </div>
      <table style={{ width: '100%', borderCollapse: 'collapse', marginTop: '.6rem', fontSize: '.85rem' }}>
        <thead><tr><th style={S.td}>断言</th><th style={S.td}>期间</th><th style={S.td}>差值(分)</th><th style={S.td}>状态</th></tr></thead>
        <tbody>
          {rows.map(it => (
            <React.Fragment key={it.assertion_id}>
              <tr onClick={() => set展开(展开 === it.assertion_id ? null : it.assertion_id)} style={{ cursor: 'pointer' }}>
                <td style={S.td}>{it.metric ?? it.assertion_id}</td>
                <td style={S.td}>{it.period ?? ''}</td>
                <td style={S.td}>{it.delta_cents ?? '—'}</td>
                <td style={S.td}>{it.status}</td>
              </tr>
              {展开 === it.assertion_id && (
                <tr><td style={{ ...S.td, opacity: .8 }} colSpan={4}>
                  <div>{it.finding ?? '（无 finding）'}</div>
                  <div style={S.muted}>证据：{it.evidence_ref ?? '—'}｜来源：{it.expect_source ?? '—'} vs {it.our_source ?? '—'}</div>
                </td></tr>
              )}
            </React.Fragment>
          ))}
        </tbody>
      </table>
    </div>
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
  useEffect(() => {
    fetch('/api/项目成本').then(r => r.json()).then(set成本)
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
        {['我在哪', '源检查板', '项目成本', '差异工作台', '数据管线', '技能'].map(t => (
          <button key={t} type="button" role="tab" aria-selected={页 === t}
                  style={{ ...S.tab(页 === t), font: 'inherit' }} onClick={() => set页(t)}>{t}</button>
        ))}
      </nav>
      {页 === '我在哪' && <我在哪 我在哪={我在哪数据} 断言={断言} 管线={管线} 技能={技能} />}
      {页 === '源检查板' && <源检查板 源检查={源检查} />}
      {页 === '项目成本' && <项目成本 成本={成本} />}
      {页 === '差异工作台' && <差异工作台 断言={断言} />}
      {页 === '数据管线' && <数据管线 管线={管线} />}
      {页 === '技能' && <技能页 技能={技能} />}
    </div>
  )
}
