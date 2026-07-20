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

function Kpi({ 标, 值, 注, 色, 小, 点 }) {
  return (
    <div className={`card kpi${点 ? ' click' : ''}`} onClick={点}>
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

// 界面说人话，机器词降级进悬停提示——这是团队四角色的一致要求（PRD 第四节）
const 人话状态 = {
  analyzed_open: '已查明·待拍板', open: '待拍板',
  closed: '已对平', closed_matched: '已对平', closed_tolerated: '容差内已闭',
  excluded: '已排除',
}
function 态chip(s) {
  const 色 = s === 'analyzed_open' || s === 'open' ? 'warn'
    : s === 'excluded' ? 'mut' : 'ok'
  return <span className={`chip ${色}`} title={s}>{人话状态[s] ?? s}</span>
}

const 金额数 = s => {
  if (s == null) return null
  const n = Number(String(s).replace(/[^0-9.-]/g, ''))
  return Number.isFinite(n) ? n : null
}

/* ---------- 今天（首页：先答问题，再给证据） ---------- */

function 今天({ 状态, 工作台, 账龄, 开票, 成本, 管线, 排程, 断言, 去 }) {
  if (!状态 && !工作台) return <骨架 />
  const 判 = 状态 && !状态.加载失败 ? 状态.页眉 : null
  const 不可对外 = 判 ? String(判.GO状态).includes('NO_GO') : true
  const 待办 = (工作台 && !工作台.加载失败 ? 工作台.断言明细 ?? [] : [])
    .filter(i => i.分组 === 'open')
    .map(i => ({ ...i, 金额: 金额数(i.差异元) }))
    .sort((a, b) => Math.abs(b.金额 ?? -1) - Math.abs(a.金额 ?? -1))
  const 核对 = 断言 && !断言.加载失败 ? 断言 : null
  const 根阻 = 成本 && !成本.加载失败 ? (成本.阻塞链?.根阻塞 ?? []) : []
  const 对 = 账龄 && !账龄.加载失败 ? 账龄.回款对账 : null
  const 票 = 开票 && !开票.加载失败 ? 开票 : null
  const 排 = 排程 && !排程.加载失败 ? 排程 : null
  const 排灯 = !排 ? ['warn', '排程状态载入中'] :
    !排.可读 ? ['warn', '排程日志暂读不到（刚部署后常见，跑过一班即恢复）'] :
    排.失败数 > 0 ? ['bad', `自动任务有 ${排.失败数} 项失败——点开看原因`] :
    排.仍在空跑数 > 0 ? ['warn', `自动任务在跑但 ${排.仍在空跑数} 项未开投递（消息发不出）`] :
    排.总执行次数 > 0 ? ['ok', '昨夜自动核对与投递正常'] : ['warn', '自动任务尚无执行记录']

  return (
    <>
      <div className={`verdict${不可对外 ? '' : ' ok'}`}>
        <div className="vtitle">
          {不可对外 ? '暂不可对外——关键账未对平，报告仅限内部使用' : '账已对平，可对外使用'}
        </div>
        {核对 && (
          <div className="vline">
            {核对.total} 项自动核对已对平 <b>{核对.closed}</b> 项，还有 <b>{待办.length || 核对.analyzed_open}</b> 项等你拍板。
          </div>
        )}
        {根阻.length > 0 && (
          <div className="vline">
            项目成本还算不出金额——{根阻[0].内容?.slice(0, 40)}…（编号 <code>{根阻[0].编号}</code>，
            {根阻[0].只有Owner可解 ? '只有你能解' : '可代办'}）。
          </div>
        )}
        <div className="vpath">
          出路：把「等你拍板」清完 + 补上权威成本基准，报告即可去水印对外。
          {判 && <> 机器判级：<code>{判.质量等级}</code> / <code>{判.报告等级}</code> / <code>{判.GO状态}</code></>}
        </div>
      </div>

      <h3 className="sec">等你拍板{待办.length ? `（${待办.length} 项，按金额从大到小）` : ''}</h3>
      {!工作台 ? <div className="card" style={{ marginTop: 12 }}><div className="skel" style={{ height: 13 }} /></div>
        : 工作台.加载失败 ? <加载失败卡 详情={工作台.加载失败} />
        : 待办.length === 0 ? <p className="empty">没有等你拍板的事——都对平了。</p> : (
        <div className="tblwrap queue">
          {待办.slice(0, 8).map(it => (
            <div key={it.断言} className="qrow">
              <div className="qmain">
                <div className="qname">{it.口径}</div>
                <div className="qsub"><code>{it.断言}</code>　{it.期间}</div>
              </div>
              <div className="qamt">
                {it.差异元 != null ? `¥${it.差异元}` : '金额待定'}
                <small>差异金额</small>
              </div>
              <button type="button" className="btn pri" onClick={() => 去('待拍板', it.断言)}>去拍板</button>
            </div>
          ))}
          {待办.length > 8 && (
            <div className="qrow">
              <div className="qmain muted">还有 {待办.length - 8} 项……</div>
              <button type="button" className="btn" onClick={() => 去('待拍板')}>看全部</button>
            </div>
          )}
        </div>
      )}

      <h3 className="sec">钱怎么样</h3>
      <div className="grid">
        <Kpi 标="回款核对" 点={() => 去('回款与账龄')}
             值={对 ? `${对.零分差月数}/${对.月数} 月已对平` : '…'} 小
             色={对 && 对.未闭月数 ? 'warn' : 'ok'}
             注={对 ? (对.未闭月数 ? `未闭 ${对.未闭月数} 月${对.最大差异 ? `·最大差异 ¥${对.最大差异.差异元}` : ''}` : '全部对平') : ''} />
        <Kpi 标="开票与税务" 点={() => 去('开票与税务')}
             值={票 ? `待处理 ${(票.开票对账?.未闭条数 ?? 0) + (票.税务对账?.未闭条数 ?? 0)} 项` : '…'} 小
             色={票 && ((票.开票对账?.未闭条数 ?? 0) + (票.税务对账?.未闭条数 ?? 0)) ? 'warn' : 'ok'}
             注={票 ? '本系统只核对不动账：未开票、未申报、未动账' : ''} />
        <Kpi 标="项目成本" 点={() => 去('项目成本')}
             值={成本 && !成本.加载失败 ? (成本.事实层?.已算金额记录数 ? '可核算' : '算不出金额') : '…'} 小
             色={成本 && !成本.加载失败 && !成本.事实层?.已算金额记录数 ? 'warn' : 'ok'}
             注="缺权威成本基准——点进看缺什么、谁能解" />
      </div>

      <div className="lightline" role="button" tabIndex={0} onClick={() => 去('系统自检')}
           onKeyDown={e => { if (e.key === 'Enter') 去('系统自检') }}>
        <span className={`light ${排灯[0]}`} />
        <span>{排灯[1]}</span>
        {管线 && !管线.加载失败 && <span>｜数据截至批次 {管线.data_as_of_batch}</span>}
        <span style={{ marginLeft: 'auto' }}>系统自检 →</span>
      </div>

      <div className="card click" style={{ marginTop: 14 }} onClick={() => 去('报告下载')}>
        <b>取报告</b>
        <div className="muted" style={{ marginTop: 5 }}>
          可下载 HTML / CSV / PDF——当前为<b>内部版·带水印</b>，不可对外；把上面的事清完即可去水印。
        </div>
      </div>
    </>
  )
}

/* ---------- 待拍板（原差异工作台：全 App 唯一动作中心） ---------- */

function 待拍板({ 台, 刷新, 初始展开 }) {
  const [分组, set分组] = useState('全部')
  const [域, set域] = useState('全部')
  const [展开, set展开] = useState(初始展开 ?? null)
  const [理由, set理由] = useState('')
  const [忙, set忙] = useState(null)
  const [提示, set提示] = useState(null)
  if (!台) return <骨架 />
  if (台.加载失败) return <加载失败卡 详情={台.加载失败} />
  const items = 台.断言明细 ?? []
  const 域列表 = ['全部', ...new Set(items.map(i => i.域).filter(Boolean))]
  const 序 = { open: 0, closed: 1, excluded: 2 }
  const rows = items
    .filter(i => (分组 === '全部' || i.分组 === 分组) && (域 === '全部' || i.域 === 域))
    .slice().sort((a, b) => (序[a.分组] ?? 9) - (序[b.分组] ?? 9))

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
        <Kpi 标="待拍板" 值={台.分组计数.open} 色={台.分组计数.open ? 'warn' : 'ok'} 注="拍完一项少一项" />
        <Kpi 标="已对平" 值={台.分组计数.closed} 色="ok" />
        <Kpi 标="已排除" 值={台.分组计数.excluded} />
        <Kpi 标="拍板留痕" 值={台.事件.总数}
             注={`App 写入 ${台.事件['App 写入']}｜已冲正 ${台.事件.已被冲正}`} />
      </div>

      <div className="card callout ok">
        <b>怎么拍：点开一行 → 写理由 → 三选一。每一板都留痕，改主意就追加冲正，历史永不涂改</b>
        <div className="sub">
          只记不改：{台.写入纪律.append_only ? '是' : '否'}｜允许静默改写：{台.写入纪律['允许静默改写'] ? '是' : '否'}｜
          改主意的做法：{台.写入纪律['改主意的做法']}
        </div>
        <div className="sub">
          账实双向核对：本台孤儿事件 {台.双向一致.本台孤儿事件数} 条 → {台.双向一致.一致 ? '一致 ✅' : '不一致 ⚠️'}
          ｜仓内未挂载 {台.双向一致.仓内未挂载事件数} 条（指向治理记录号）
        </div>
      </div>

      <div className="formrow" style={{ marginTop: 16 }}>
        <span className="muted">状态</span>
        <select className="select" value={分组} onChange={e => set分组(e.target.value)}>
          {['全部', 'open', 'closed', 'excluded'].map(d =>
            <option key={d} value={d}>{d === '全部' ? '全部' : 人话状态[d]}</option>)}</select>
        <span className="muted">业务域</span>
        <select className="select" value={域} onChange={e => set域(e.target.value)}>
          {域列表.map(d => <option key={d}>{d}</option>)}</select>
        <span className="muted">{rows.length} 项（待拍板在前）</span>
      </div>

      <Tbl>
        <thead><tr>
          <th>核对项</th><th>口径</th><th>期间</th>
          <th className="num">差异（元）</th><th>状态</th><th>现行决策</th>
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

/* ---------- 报告下载（原报告中心） ---------- */

function 报告下载({ 中心 }) {
  if (!中心) return <骨架 />
  if (中心.加载失败) return <加载失败卡 详情={中心.加载失败} />
  const 水 = 中心.水印, 判 = 中心.交付判据
  return (
    <>
      <div className="grid">
        <Kpi 标="可否对外" 值={判.delivery_allowed ? '可对外' : '仅限内部'} 小
             色={判.delivery_allowed ? 'ok' : 'bad'} 注={`机器判级 ${中心.页眉.报告等级}`} />
        <Kpi 标="质量等级" 值={中心.页眉.质量等级} />
        <Kpi 标="交付状态" 值={中心.页眉.delivery状态} 小 色={判.delivery_allowed ? 'ok' : 'bad'} />
        <Kpi 标="导出登记" 值={中心.导出登记.条数} 注="每次下载都留痕，不可改写" />
      </div>

      <div className="card callout bad">
        <b>内部版——{水.生效中 ? '带水印，不可对外发出' : '水印已解除'}</b>
        {水.文案 && <div className="sub" style={{ fontFamily: 'var(--mono)' }}>{水.文案}</div>}
        <div className="sub">覆盖格式：{水.覆盖格式.join(' / ')}｜可关闭：{水.可关闭 ? '是' : '否'}</div>
        <div className="sub">去水印条件：{水.去除条件}</div>
      </div>

      <h3 className="sec">八份报告 × 三格式（点击即下载）</h3>
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

      <h3 className="sec">PDF 说明</h3>
      <div className="card callout warn" style={{ marginTop: 12 }}>
        <div>{中心.PDF策略.说明}</div>
        <div className="sub">中文渲染：{中心.PDF策略.中文渲染}</div>
      </div>

      {中心.导出登记.记录.length > 0 && (
        <>
          <h3 className="sec">下载留痕（最近 {中心.导出登记.记录.length} 条）</h3>
          <Tbl>
            <thead><tr>
              <th>号</th><th>格式</th><th>防篡改校验码</th>
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

/* ---------- 重新核算（原影响重跑，收进数据底账） ---------- */

function 重新核算({ 图, 选中资产, 选资产, 刷新 }) {
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
      <div className="card callout" style={{ marginTop: 12 }}>
        <b>什么时候用：改动了某份源数据后，把受它牵连的数全部重新算一遍</b>
        <div className="sub">
          牵一发动全身——选中源文件即可预览影响面；重算旧版本全保留（
          {图.重跑纪律.覆盖旧版本 ? '会覆盖' : '不覆盖'}、处置 <code>{图.重跑纪律.旧版本处置}</code>），
          不许借重算升报告等级：{图.重跑纪律.允许借重跑升报告等级 ? '允许' : '不允许'}。
        </div>
      </div>

      <h3 className="sec">① 选中源数据</h3>
      {/* 本区第一个 select 必须是资产选择器——E2E 用 select.first 选中它 */}
      <select className="select" style={{ minWidth: '22rem', marginTop: 10 }} value={选中资产 ?? ''}
              onChange={e => { 选资产(e.target.value); set结果(null); set提示(null) }}>
        <option value="">— 选一份原始数据 —</option>
        {图.血缘.资产.map(a => (
          <option key={a.资产} value={a.资产}>{a.资产}（{a.域}，{a.派生表数} 张派生表）</option>
        ))}
      </select>

      {下 && (
        <>
          <h3 className="sec">② 会牵连什么（由数据来龙去脉算出）</h3>
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
            <div style={{ marginTop: 4 }}>受影响核对域：{下.受影响断言域.join('、') || '—'}</div>
            <div style={{ marginTop: 4 }}>受影响报告：{下.受影响报告.join('、') || '—'}</div>
          </div>

          <h3 className="sec">③ 发起重算</h3>
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
          <h3 className="sec">历史重算</h3>
          <Tbl>
            <thead><tr><th>轮次号</th><th>步骤</th><th>状态</th><th>起止</th></tr></thead>
            <tbody>{图.本机重跑记录.最近.slice().reverse().map(r => (
              <tr key={r.轮次号}>
                <td><code>{r.轮次号}</code></td>
                <td>{r.步骤}</td>
                <td><span className={`chip ${r.状态 === 'completed' ? 'ok' : 'warn'}`}>{r.状态 === 'completed' ? '已完成' : r.状态}</span></td>
                <td className="muted">{r.起于} → {r.止于}</td>
              </tr>
            ))}</tbody>
          </Tbl>
        </>
      )}
    </>
  )
}

/* ---------- 操作留痕（原审计日志，收进数据底账） ---------- */

function 操作留痕({ 审计 }) {
  if (!审计) return <骨架 />
  if (审计.加载失败) return <加载失败卡 详情={审计.加载失败} />
  const 契 = 审计.契约, 访 = 审计.访问模式
  return (
    <>
      <div className="grid">
        <Kpi 标="留痕总数" 值={审计.总数} 注="只记不改，可随时对质" />
        {Object.entries(审计.按动作).slice(0, 3).map(([k, v]) => (
          <Kpi key={k} 标={k} 值={v} />
        ))}
      </div>

      <div className="card callout ok">
        <b>访问模式：{访.模式}</b>
        <div className="sub">应用内登录：{访.应用内登录 ? '有' : '无'}｜生产鉴权：{访.生产鉴权}</div>
        <div className="sub">{访.说明}</div>
      </div>

      <h3 className="sec">操作流水（最近在前）</h3>
      {审计.事件.length === 0 ? <p className="empty">暂无记录——做一次拍板或下载后即会留痕。</p> : (
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
      <details>
        <summary>留痕契约（审计口径详情）</summary>
        <div className="muted" style={{ marginTop: 6 }}>
          政策版本 <code>{契.政策版本}</code>｜只记不改：{契.append_only ? '是' : '否'}｜
          允许记原始载荷：{契.允许记原始载荷 ? '是' : '否'}｜允许记业务明文：{契.允许记业务明文 ? '是' : '否'}｜
          必填字段：{契.必填字段.join('、')}
        </div>
      </details>
    </>
  )
}

/* ---------- 排程健康（系统自检主体） ---------- */

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
        <Kpi 标="有记录的自动任务" 值={排程.有记录的技能数} />
        <Kpi 标="最近一次失败" 值={排程.失败数} 色={排程.失败数 ? 'bad' : 'ok'} />
        <Kpi 标="空跑中（未开投递）" 值={排程.仍在空跑数} 色={排程.仍在空跑数 ? 'warn' : 'ok'} 注="消息不会真发出" />
        <Kpi 标="总执行次数" 值={排程.总执行次数} />
      </div>
      <div className={`card callout ${好 ? 'ok' : 'warn'}`}>
        <b>{排程.结论}</b>
        <div className="sub">{排程.诚实边界}</div>
      </div>
      <Tbl>
        <thead><tr>
          <th>自动任务</th><th>约定时刻</th><th>最近一次</th>
          <th className="num">距今</th><th>结果</th><th>投递</th>
        </tr></thead>
        <tbody>{排程.逐项.map(x => (
          <tr key={x.技能}>
            <td><code>{x.技能}</code></td>
            <td className="muted">{x.约定时刻}</td>
            <td>{x.最近一次 ?? <span className="tone-bad">从未跑过</span>}</td>
            <td className="num">{x.距今小时 == null ? '—' : `${x.距今小时} 小时前`}</td>
            <td>{x.成功 === true ? <span className="chip ok">成功</span>
              : x.成功 === false ? <span className="chip bad" title={`rc=${x.退出码}`}>失败</span>
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

/* ---------- 数据接入（原数据管线，收进数据底账） ---------- */

function 数据接入({ 管线 }) {
  if (!管线) return <骨架 />
  if (管线.加载失败) return <加载失败卡 详情={管线.加载失败} />
  const 表 = Object.entries(管线.staging_tables ?? {}).sort((a, b) => (b[1].rows ?? 0) - (a[1].rows ?? 0))
  return (
    <>
      <div className="grid">
        <Kpi 标="接入原始文件" 值={管线.raw_assets_registered ?? '—'} 注="内容寻址入仓，防篡改" />
        <Kpi 标="已接入原始记录" 值={(管线.staging_rows_total ?? 0).toLocaleString('zh')}
             注={`截至批次 ${管线.data_as_of_batch}——只说明数据进来了，不代表账对了`} />
        <Kpi 标="质量档位" 值={管线.quality_grade_current ?? '—'} 小
             注={`未决质量卡点 ${管线.quality_blockers_open ?? 0} 项`} />
      </div>
      <div className="card" style={{ marginTop: 14 }}>
        <div className="muted">各表行数（对数轴）</div>
        <Chart height={`${Math.max(表.length * 1.7, 10)}rem`} option={{
          tooltip: {}, grid: { left: 8, right: 48, top: 8, bottom: 8, containLabel: true },
          xAxis: { type: 'log', minorSplitLine: { show: false } },
          yAxis: { type: 'category', data: 表.map(([名]) => 名).reverse(), axisLabel: { fontSize: 10 } },
          series: [{ type: 'bar', data: 表.map(([, 值]) => 值.rows ?? 0).reverse(),
            label: { show: true, position: 'right', formatter: p => p.value.toLocaleString('zh') } }],
        }} />
      </div>
      {管线.reconciliation_status && (
        <div className="card callout">
          <b>对账现状</b>
          <div className="sub">{管线.reconciliation_status}</div>
        </div>
      )}
    </>
  )
}

/* ---------- 源清单（原源检查板，收进数据底账） ---------- */

function 源清单({ 源检查 }) {
  if (!源检查) return <骨架 />
  if (源检查.加载失败) return <加载失败卡 详情={源检查.加载失败} />
  const 协议 = 源检查.矩阵协议, 覆盖 = 源检查.覆盖矩阵, 鲜 = 源检查.新鲜度, 派生 = 源检查.派生层
  return (
    <>
      <div className="grid">
        <Kpi 标="登记数据源文件" 值={覆盖.资产合计} />
        <Kpi 标="数据批次" 值={鲜.数据批次 || '—'} 小 />
        <Kpi 标="派生表 / 行" 值={`${派生.表数} / ${(派生.行合计 ?? 0).toLocaleString('zh')}`} />
        <Kpi 标="新鲜度" 值={鲜.stale ? '已过期' : '新鲜'} 色={鲜.stale ? 'bad' : 'ok'} />
      </div>
      <p className="muted" style={{ marginTop: 10 }}>{鲜.提示}</p>

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
      <details>
        <summary>正式源检查矩阵（协议态详情）</summary>
        <div className="muted" style={{ marginTop: 6 }}>
          schema <code>{协议.schema || '—'}</code>｜阶段 {协议.阶段 || '—'}｜状态 {协议.状态 || '—'}｜
          已提交源行 {协议.已提交源行}｜{协议.说明}
        </div>
      </details>
    </>
  )
}

/* ---------- 数据底账（后台：四节合一） ---------- */

function 数据底账({ 源检查, 管线, 图, 选中资产, 选资产, 刷新, 审计 }) {
  return (
    <>
      <h3 className="sec">一、数据从哪来</h3>
      <源清单 源检查={源检查} />
      <h3 className="sec" style={{ marginTop: 34 }}>二、接入了多少</h3>
      <数据接入 管线={管线} />
      <h3 className="sec" style={{ marginTop: 34 }}>三、重新核算（改动源数据后）</h3>
      <重新核算 图={图} 选中资产={选中资产} 选资产={选资产} 刷新={刷新} />
      <h3 className="sec" style={{ marginTop: 34 }}>四、操作留痕</h3>
      <操作留痕 审计={审计} />
    </>
  )
}

/* ---------- 治理详情（原我在哪核心，折叠进系统自检） ---------- */

function 治理详情({ 我 }) {
  if (!我 || 我.加载失败) return null
  const 状 = 我?.当前状态
  const 卡 = 我?.卡住的事 ?? []
  const 阶段 = 我?.路线图?.阶段 ?? []
  if (!状) return null
  return (
    <details style={{ marginTop: 22 }}>
      <summary>治理详情（版本、卡住的事、路线图——给审计与技术看）</summary>
      <Tbl><tbody>
        <tr><td className="muted" style={{ width: '9rem' }}>版本</td><td><code>{状.版本}</code></td></tr>
        <tr><td className="muted">进行到哪</td><td>
          <code>{状.阶段}</code> · <code>{状.分期}</code> · <code>{状.任务}</code></td></tr>
        <tr><td className="muted">进度</td><td>{状.进度}</td></tr>
        <tr><td className="muted">报告可信度</td><td>{状.报告可信度}</td></tr>
        <tr><td className="muted">业务结论</td><td><b>{状.业务结论}</b></td></tr>
        <tr><td className="muted">证据状态</td><td>{状.证据状态}</td></tr>
      </tbody></Tbl>
      {卡.length > 0 && (
        <Tbl>
          <thead><tr><th>编号</th><th>什么事</th><th>谁能解</th><th>卡了多久</th></tr></thead>
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
      <Tbl>
        <thead><tr><th>阶段</th><th>名称</th><th>状态</th></tr></thead>
        <tbody>{阶段.map(s => (
          <tr key={s.id}>
            <td><code>{s.id}</code></td><td>{s.name}</td>
            <td><span className={`chip ${s.status === '有效' ? 'ok' : 'warn'}`}>{s.status}</span></td>
          </tr>
        ))}</tbody>
      </Tbl>
      <p className="foot">更新于 {我.更新于}｜{我.同源}</p>
    </details>
  )
}

/* ---------- 系统自检（后台） ---------- */

function 系统自检({ 排程, 技能, 我 }) {
  return (
    <>
      <排程健康 排程={排程} />
      <h3 className="sec" style={{ marginTop: 30 }}>自动化任务清单</h3>
      {!技能 ? <div className="card" style={{ marginTop: 12 }}><div className="skel" style={{ height: 13 }} /></div>
        : 技能.加载失败 ? <加载失败卡 详情={技能.加载失败} /> : (
        <Tbl>
          <thead><tr><th>任务</th><th>排程</th><th>外部依赖</th><th>迁移待办</th></tr></thead>
          <tbody>
            {(技能.skills ?? []).map(it => (
              <tr key={it.id}>
                <td>{it.名称 ?? it.id}</td>
                <td className="muted">{(it.排程 ?? []).length ? it.排程.join('、') : '—'}</td>
                <td className="muted">{(it.外部依赖 ?? []).length ? it.外部依赖.join('、') : '—'}</td>
                <td>{it.本地路径硬编码 > 0
                  ? <span className="chip warn">本地路径硬编码 {it.本地路径硬编码} 处</span>
                  : <span className="chip ok">无</span>}</td>
              </tr>
            ))}
          </tbody>
        </Tbl>
      )}
      <治理详情 我={我} />
    </>
  )
}

/* ---------- 回款与账龄（原账龄回款） ---------- */

function 回款与账龄({ 账龄 }) {
  if (!账龄) return <骨架 />
  if (账龄.加载失败) return <加载失败卡 详情={账龄.加载失败} />
  const 对 = 账龄.回款对账, 恒 = 账龄.账龄恒等式, 构 = 账龄.账龄结构层
  return (
    <>
      <div className="grid">
        <Kpi 标="核对月数" 值={对.月数} />
        <Kpi 标="已对平月数" 值={对.零分差月数} 色="ok" />
        <Kpi 标="未闭月数" 值={对.未闭月数} 色={对.未闭月数 ? 'warn' : 'ok'} />
        <Kpi 标="最大差异" 值={对.最大差异 ? `¥${对.最大差异.差异元}` : '—'} 注={对.最大差异?.期间 ?? ''} />
      </div>

      <h3 className="sec">回款逐月核对（真实分差）</h3>
      <Tbl>
        <thead><tr>
          <th>核对项</th><th>口径</th><th>期间</th>
          <th className="num">差异（元）</th><th>状态</th>
        </tr></thead>
        <tbody>{对.逐月.map(m => (
          <tr key={m.断言}>
            <td><code>{m.断言}</code></td>
            <td>{m.口径}</td>
            <td>{m.期间}</td>
            <td className={`num ${m.差异分 ? 'tone-warn' : 'tone-ok'}`}
                style={{ fontWeight: m.差异分 ? 700 : 400 }}>
              {m.差异元 === null ? '—' : `¥${m.差异元}`}</td>
            <td>{态chip(m.状态)}</td>
          </tr>
        ))}</tbody>
      </Tbl>

      <h3 className="sec">账龄底数核对（恒等式）</h3>
      <Tbl>
        <thead><tr><th>核对项</th><th>口径</th><th>快照</th>
          <th className="num">差异（分）</th><th>状态</th></tr></thead>
        <tbody>{恒.map(r => (
          <tr key={r.断言}>
            <td><code>{r.断言}</code></td><td>{r.口径}</td>
            <td className="muted">{r.快照}</td>
            <td className={`num ${r.差异分 === 0 ? 'tone-ok' : 'tone-warn'}`}>{r.差异分}</td>
            <td>{态chip(r.状态)}</td>
          </tr>
        ))}</tbody>
      </Tbl>

      <h3 className="sec">账龄结构（金额仍被阻断）</h3>
      <div className="card callout warn" style={{ marginTop: 12 }}>
        <div>{账龄.诚实边界}</div>
        <div className="sub">
          源泳道 {构.源泳道数} 条；优先事项 {构.优先事项数} 条；允许作经营依据：{构.允许作经营依据 ? '是' : '否'}
        </div>
      </div>
      <ul className="muted">{构.限制.map((t, i) => <li key={i}>{t}</li>)}</ul>
    </>
  )
}

/* ---------- 核对明细表（开票与税务三个域共用） ---------- */

function 断言表({ 块, 标题 }) {
  return (
    <>
      <h3 className="sec">{标题}（真实分差 {块.条数} 条）</h3>
      <Tbl>
        <thead><tr>
          <th>核对项</th><th>口径</th><th>期间</th>
          <th className="num">差异（元）</th><th>状态</th>
        </tr></thead>
        <tbody>{块.逐条.map(r => (
          <tr key={r.断言}>
            <td><code>{r.断言}</code></td>
            <td>{r.口径}</td>
            <td>{r.期间}</td>
            <td className={`num ${r.差异分 ? 'tone-warn' : 'tone-ok'}`}
                style={{ fontWeight: r.差异分 ? 700 : 400 }}>
              {r.差异元 === null ? '—' : `¥${r.差异元}`}</td>
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

/* ---------- 开票与税务（原开票纳税） ---------- */

function 开票与税务({ 开票 }) {
  if (!开票) return <骨架 />
  if (开票.加载失败) return <加载失败卡 详情={开票.加载失败} />
  const 红 = 开票.红线, 政 = 开票.税务政策证据
  const 红线项 = Object.entries(红)
  const 红线全零 = 红线项.every(([, v]) => v === 0)
  return (
    <>
      <div className="grid">
        <Kpi 标="开票核对" 值={开票.开票对账.条数} 注={`待处理 ${开票.开票对账.未闭条数}`}
             色={开票.开票对账.未闭条数 ? 'warn' : 'ok'} />
        <Kpi 标="税务核对" 值={开票.税务对账.条数} 注={`待处理 ${开票.税务对账.未闭条数}`}
             色={开票.税务对账.未闭条数 ? 'warn' : 'ok'} />
        <Kpi 标="贷款核对" 值={开票.贷款对账.条数} 注={`已对平 ${开票.贷款对账.零分差条数}`} 色="ok" />
        <Kpi 标="系统动过账吗" 值={红线全零 ? '没有' : '有！'} 小
             色={红线全零 ? 'ok' : 'bad'} 注="本系统只核对：不开票、不申报、不动账" />
      </div>

      <断言表 块={开票.开票对账} 标题="开票核对" />
      <断言表 块={开票.税务对账} 标题="税务核对" />
      <断言表 块={开票.贷款对账} 标题="贷款核对" />

      <h3 className="sec">税务政策：证据缺口与风险提示（{政.证据完备项目数}/{政.项目数} 证据完备，不作资格判断）</h3>
      <Tbl>
        <thead><tr><th>项目</th><th>风险</th><th>风险提示</th><th>证据缺口</th></tr></thead>
        <tbody>{政.逐项.map(p => (
          <tr key={p.项目}>
            <td>{p.项目}</td>
            <td><span className={`chip ${p.风险等级 === 'high' ? 'bad' : 'warn'}`}>{p.风险等级 === 'high' ? '高' : '中'}</span></td>
            <td>{p.风险提示}</td>
            <td>{p.证据缺口}</td>
          </tr>
        ))}</tbody>
      </Tbl>

      <details>
        <summary>红线动作逐项计数（证明系统未动账）</summary>
        <Tbl>
          <thead><tr><th>动作</th><th className="num">事实计数</th></tr></thead>
          <tbody>{红线项.map(([k, v]) => (
            <tr key={k}><td>{k}</td>
              <td className={`num ${v === 0 ? 'tone-ok' : 'tone-bad'}`} style={{ fontWeight: 700 }}>{v}</td></tr>
          ))}</tbody>
        </Tbl>
      </details>
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
          <div className="sub"><b>出路：</b>补上权威成本基准（见下「卡在哪」），补齐即可自动核算。</div>
        </div>
      )}
      <div className="grid">
        <Kpi 标="项目记录" 值={层.记录数} 注={`已算出金额 ${层.已算金额记录数}`} />
        <Kpi 标="成本类别槽位" 值={构.成本类别.length} />
        <Kpi 标="指标槽位" 值={构.事实指标.length} />
      </div>

      <h3 className="sec">卡在哪、谁能解</h3>
      <Tbl>
        <thead><tr><th>编号</th><th>什么事</th><th>谁能解</th><th>已卡</th></tr></thead>
        <tbody>{阻.根阻塞.map(b => (
          <tr key={b.编号}>
            <td><code>{b.编号}</code></td><td>{b.内容}</td>
            <td>{b.只有Owner可解 ? <span className="chip bad">只有你能解</span> : <span className="chip mut">可代办</span>}</td>
            <td>{b.已卡}</td>
          </tr>
        ))}</tbody>
      </Tbl>

      <h3 className="sec">项目清单（金额待基准解锁）</h3>
      <Tbl>
        <thead><tr>
          <th>记录号</th><th>项目</th><th>计算状态</th><th>金额已计算</th>
        </tr></thead>
        <tbody>{成本.记录.map(r => (
          <tr key={r.记录号}>
            <td><code>{r.记录号}</code></td>
            <td><code>{r.项目实体}</code></td>
            <td><span className="chip warn" title={r.计算状态}>待基准解锁</span></td>
            <td>{r.金额已计算 ? '是' : '否'}</td>
          </tr>
        ))}</tbody>
      </Tbl>

      <details>
        <summary>结构与派生层详情（技术口径）</summary>
        <p className="muted" style={{ marginTop: 8 }}>
          状态 <code>{层.状态}</code>｜公式 {层.公式版本}｜映射 {层.映射版本}｜生成于 {层.生成于}</p>
        <p className="muted">成本类别：{构.成本类别.join('、')}</p>
        <p className="muted">指标：{构.事实指标.join('、')}</p>
        <Tbl>
          <thead><tr><th>可下钻表</th><th className="num">行数</th></tr></thead>
          <tbody>{成本.可下钻派生层.map(t => (
            <tr key={t.表}><td><code>{t.表}</code></td>
              <td className="num">{(t.行数 ?? 0).toLocaleString('zh')}</td></tr>
          ))}</tbody>
        </Tbl>
      </details>
    </>
  )
}

/* ---------- 壳：导航结构与图标 ---------- */

const 导航组 = [
  ['总览', ['今天']],
  ['钱', ['回款与账龄', '开票与税务', '项目成本']],
  ['拍板', ['待拍板']],
  ['报告', ['报告下载']],
  ['后台', ['数据底账', '系统自检']],
]
const 全部页 = 导航组.flatMap(([, xs]) => xs)

// 图标只能是无文本的 svg：E2E 用 textContent === 页名 严格比对页签，任何文字节点都会破坏它
const 线属性 = { fill: 'none', stroke: 'currentColor', strokeWidth: 1.8, strokeLinecap: 'round', strokeLinejoin: 'round' }
function 图({ d }) {
  return <svg width="15" height="15" viewBox="0 0 24 24" aria-hidden="true" focusable="false" {...线属性}><path d={d} /></svg>
}
const 图标 = {
  今天: <图 d="M3 11.5 12 4l9 7.5M5.5 9.8V20h13V9.8" />,
  回款与账龄: <图 d="M12 3a9 9 0 1 1 0 18 9 9 0 0 1 0-18zM12 7v5l3.5 2" />,
  开票与税务: <图 d="M6 3h12v18l-2-1.4L14 21l-2-1.4L10 21l-2-1.4L6 21V3zM9 8h6M9 12h6" />,
  项目成本: <图 d="M12 3a9 9 0 1 0 9 9h-9V3zM15 3.5A9 9 0 0 1 20.5 9H15V3.5z" />,
  待拍板: <图 d="M6 4h12M6 4v3l4 4-4 4v3M18 4v3l-4 4 4 4v3M6 18h12" />,
  报告下载: <图 d="M7 3h7l4 4v14H7V3zM14 3v4h4M12 11v6M9.5 14.5 12 17l2.5-2.5" />,
  数据底账: <图 d="M12 3c4.4 0 8 1.3 8 3s-3.6 3-8 3-8-1.3-8-3 3.6-3 8-3zM4 6v12c0 1.7 3.6 3 8 3s8-1.3 8-3V6M4 12c0 1.7 3.6 3 8 3s8-1.3 8-3" />,
  系统自检: <图 d="M3 12h4l2.5-6 4 12 2.5-6h5" />,
}

export default function App() {
  const [页, set页] = useState('今天')
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
  const [拍板跳转, set拍板跳转] = useState(null)
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

  const 去 = (p, 断言id) => { set拍板跳转(断言id ?? null); set页(p) }

  // 导航上的注意点：数据说有事，入口就亮点——不用逐页翻
  const 注意点 = {
    今天: (我在哪数据?.卡住的事?.length ?? 0) > 0 ? 'warn' : null,
    待拍板: (工作台?.分组计数?.open ?? 0) > 0 ? 'warn' : null,
    系统自检: !排程 || 排程.加载失败 ? null
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
    if (e.key === 'ArrowDown' || e.key === 'ArrowRight') { e.preventDefault(); 去(全部页[(i + 1) % 全部页.length]) }
    else if (e.key === 'ArrowUp' || e.key === 'ArrowLeft') { e.preventDefault(); 去(全部页[(i - 1 + 全部页.length) % 全部页.length]) }
  }

  return (
    <div className="shell">
      <aside className="side">
        <div className="brand">
          <h1>KMFA 经营分析</h1>
          <small>先答问题，再给证据·不装健康</small>
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
                        onClick={() => 去(t)}>{图标[t]}<span>{t}</span>{注意点[t] && <i className={`dot ${注意点[t]}`} aria-hidden="true" />}</button>
              ))}
            </div>
          ))}
        </nav>
      </aside>

      <div className="main">
        <header className="topbar">
          <h2>{页}</h2>
          {状态 && !状态.加载失败 && <>
            <span className="badge" title="数据质量档位（机器判级）">质量 <b>{状态.页眉.质量等级}</b></span>
            <span className="badge" title="报告可信度（机器判级）">报告 <b>{状态.页眉.报告等级}</b></span>
            <span className={`badge${String(状态.页眉.GO状态).includes('NO_GO') ? ' risk' : ''}`}
                  title="NO_GO＝暂不可对外：关键账未对平，报告仅限内部">
              <b>{状态.页眉.GO状态}</b></span>
          </>}
          {管线 && !管线.加载失败 && 管线.data_as_of_batch &&
            <span className="meta">数据截至批次 {管线.data_as_of_batch}</span>}
        </header>

        <div className="content">
          <div key={页} className="panel" role="tabpanel" aria-label={页}>
            {页 === '今天' && <今天 状态={状态} 工作台={工作台} 账龄={账龄} 开票={开票}
              成本={成本} 管线={管线} 排程={排程} 断言={断言} 去={去} />}
            {页 === '回款与账龄' && <回款与账龄 账龄={账龄} />}
            {页 === '开票与税务' && <开票与税务 开票={开票} />}
            {页 === '项目成本' && <项目成本 成本={成本} />}
            {页 === '待拍板' && <待拍板 台={工作台} 刷新={取工作台} 初始展开={拍板跳转} />}
            {页 === '报告下载' && <报告下载 中心={中心} />}
            {页 === '数据底账' && <数据底账 源检查={源检查} 管线={管线} 图={影响}
              选中资产={选中资产} 选资产={a => { set选中资产(a); 取影响(a) }} 刷新={取影响} 审计={审计} />}
            {页 === '系统自检' && <系统自检 排程={排程} 技能={技能} 我={我在哪数据} />}
          </div>
        </div>
      </div>
    </div>
  )
}
