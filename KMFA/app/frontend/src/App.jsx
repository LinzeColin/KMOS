import React, { useEffect, useState } from 'react'

const S = {
  body: { fontFamily: '-apple-system, "PingFang SC", sans-serif', maxWidth: '64rem', margin: '0 auto', padding: '2rem' },
  header: { display: 'flex', gap: '.75rem', alignItems: 'baseline', flexWrap: 'wrap' },
  badge: { padding: '.15rem .6rem', borderRadius: 999, border: '1px solid currentColor', fontSize: '.85rem' },
  grid: { display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(14rem, 1fr))', gap: '1rem', marginTop: '1.5rem' },
  card: { border: '1px solid rgba(127,127,127,.35)', borderRadius: '.75rem', padding: '1rem' },
  num: { fontSize: '1.8rem', fontWeight: 700 },
  muted: { opacity: .65, fontSize: '.85rem' },
  td: { padding: '.3rem .4rem', borderBottom: '1px solid rgba(127,127,127,.2)', textAlign: 'left' },
}

export default function App() {
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
      <div style={S.grid}>
        <div style={S.card}>
          <div style={S.muted}>对账断言（closed / 总数）</div>
          <div style={S.num}>{断言 ? `${断言.closed} / ${断言.total}` : '…'}</div>
          <div style={S.muted}>{断言 ? `analyzed-open ${断言.analyzed_open}` : ''}</div>
        </div>
        <div style={S.card}>
          <div style={S.muted}>私有派生层数据行</div>
          <div style={S.num}>{管线 ? (管线.staging_rows_total ?? 0).toLocaleString('zh') : '…'}</div>
          <div style={S.muted}>{管线 ? `截止批次 ${管线.data_as_of_batch}` : ''}</div>
        </div>
        <div style={S.card}>
          <div style={S.muted}>技能</div>
          <div style={S.num}>{技能 ? 技能.count : '…'}</div>
          <div style={S.muted}>全部迁云计划中</div>
        </div>
      </div>
      <div style={{ ...S.card, marginTop: '1rem' }}>
        <div style={S.muted}>断言清单</div>
        <table style={{ width: '100%', borderCollapse: 'collapse', marginTop: '.5rem', fontSize: '.85rem' }}>
          <thead><tr><th style={S.td}>断言</th><th style={S.td}>期间</th><th style={S.td}>状态</th></tr></thead>
          <tbody>
            {断言?.items?.slice().sort((a, b) => String(a.status).localeCompare(String(b.status))).map(it => (
              <tr key={it.assertion_id}>
                <td style={S.td}>{it.metric ?? it.assertion_id}</td>
                <td style={S.td}>{it.period ?? ''}</td>
                <td style={S.td}>{it.status}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
