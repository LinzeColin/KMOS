import React, { useEffect, useMemo, useState } from 'react'

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

function 概览({ 断言, 管线, 技能 }) {
  return (
    <>
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

export default function App() {
  const [页, set页] = useState('概览')
  const [状态, set状态] = useState(null)
  const [断言, set断言] = useState(null)
  const [管线, set管线] = useState(null)
  const [技能, set技能] = useState(null)
  useEffect(() => {
    fetch('/api/状态').then(r => r.json()).then(set状态)
    fetch('/api/断言').then(r => r.json()).then(set断言)
    fetch('/api/数据管线').then(r => r.json()).then(set管线)
    fetch('/api/技能').then(r => r.json()).then(set技能)
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
        {['概览', '差异工作台'].map(t => (
          <span key={t} style={S.tab(页 === t)} onClick={() => set页(t)}>{t}</span>
        ))}
      </nav>
      {页 === '概览' ? <概览 断言={断言} 管线={管线} 技能={技能} /> : <差异工作台 断言={断言} />}
    </div>
  )
}
