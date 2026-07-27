import React, { useEffect, useState } from 'react'
import './public-shell.css'

// KMFA 首页 = KMFA 本体(经营驾驶舱)的公开门面。
// 铁律:只讲能力与工程质量,不呈现任何真实经营数字;经营数据默认私有。
const MODULES = [
  {
    key: 'today',
    code: '01',
    title: '今天',
    eyebrow: 'TODAY',
    status: '驾驶舱内已上线',
    summary: '一屏看清昨天发生了什么、自动任务跑得怎样、哪些事等你拍板。',
    detail: '「今天」是驾驶舱的经营战报首页:近 24 小时自动任务战报、待拍板队列与断链自检入口汇聚在一屏,打开系统的第一眼就是结论,而不是一堆表格。',
    facts: ['近 24 小时自动任务战报', '待拍板事项一键直达', '断链自检状态一眼可见'],
  },
  {
    key: 'cash',
    code: '02',
    title: '回款与账龄',
    eyebrow: 'RECEIVABLES',
    status: '驾驶舱内已上线',
    summary: '谁欠钱、欠了多久、先催谁,账龄与逐月差异一屏讲清。',
    detail: '回款与账龄把应收按客户与时间排开,配逐月差异图与人话金额(万/亿缩写与精确值并存);每一个数字都能下钻到数据底账,不做估算图、不摆演示数据。',
    facts: ['账龄与逐月差异可视化', '人话金额与精确值并存', '每个数字可下钻到底账'],
  },
  {
    key: 'tax',
    code: '03',
    title: '开票与税务',
    eyebrow: 'INVOICES & TAX',
    status: '驾驶舱内已上线',
    summary: '开票、税负与口径一致性,数字与底账一一对应。',
    detail: '开票与税务呈现开票台账与税负口径,与数据底账同一来源;口径差异不藏在备注里,而是进入待拍板闭环,由拍板事件留痕。',
    facts: ['开票台账与税负口径', '与数据底账同源一致', '差异进入待拍板闭环'],
  },
  {
    key: 'cost',
    code: '04',
    title: '项目成本',
    eyebrow: 'COSTS',
    status: '驾驶舱内已上线',
    summary: '每个项目花了多少、结构如何、走势怎样,支出到行级。',
    detail: '项目成本按项目与分项展开成本结构,逐月走势一屏可见;任何一笔汇总都能追溯到支出行,不存在讲不出来历的数字。',
    facts: ['项目与分项成本结构', '逐月走势一屏可见', '支出行级全程可追溯'],
  },
  {
    key: 'decide',
    code: '05',
    title: '待拍板',
    eyebrow: 'DECISIONS',
    status: '已上线·全留痕',
    summary: '差异、例外与闭案:先讲清"会牵连什么",再请老板拍板。',
    detail: '待拍板把每个差异的影响面(受影响核对域、牵连数据)讲清之后才允许闭案;每一次拍板写入留痕事件,可回溯、不可静默改数。',
    facts: ['影响面先行讲清', '拍板事件全程留痕', '闭案之后仍可回溯'],
  },
  {
    key: 'report',
    code: '06',
    title: '报告下载',
    eyebrow: 'REPORTS',
    status: '已上线·真下载',
    summary: '三种口径的经营报告,一键真下载,与页面数字同源。',
    detail: '报告下载提供三种口径的经营报告文件,一键导出;报告数字与驾驶舱页面同源同链,历史版本全保留,重算不覆盖旧账。',
    facts: ['三种口径一键导出', '报告与页面数字同源', '历史版本全部保留'],
  },
]

const MODULE_KEYS = new Set(MODULES.map((item) => item.key))

const CHAIN_STEPS = [
  { num: '1', title: '事实底账', text: '凭证与台账逐行入库,行级可查,是全部数字的唯一来源。' },
  { num: '2', title: '自动核对', text: '多个核对域交叉校验,差异自动浮出,不靠人肉盯表。' },
  { num: '3', title: '影响面', text: '每个差异先讲清"会牵连什么",再谈怎么处理。' },
  { num: '4', title: '拍板留痕', text: '决策写成事件,闭案可回溯;重算时旧版本全保留。' },
]

function Icon({ name }) {
  const paths = {
    today: <><rect x="4" y="5" width="16" height="15" rx="2" /><path d="M4 9.5h16M8 3.5v3M16 3.5v3" /><path d="m9 14.5 2 2 4-4" /></>,
    cash: <><circle cx="12" cy="12" r="8.5" /><path d="m9 8 3 4 3-4M12 12v5M9.5 13.5h5" /></>,
    tax: <><path d="M6 3.5h12v17l-2-1.5-2 1.5-2-1.5-2 1.5-2-1.5-2 1.5z" /><path d="M9 8.5h6M9 12h6" /></>,
    cost: <><path d="M3.5 20h17" /><path d="M6 20v-7M11 20V5M16 20v-10M20.5 20V9" /></>,
    decide: <><path d="M12 3.5l7 3v5.5c0 4.5-3 7.6-7 8.5-4-.9-7-4-7-8.5V6.5z" /><path d="m9 11.5 2 2 4-4" /></>,
    report: <><path d="M5 3.5h10l4 4v13H5z" /><path d="M15 3.5v4h4" /><path d="M12 10.5v6m-2.5-2.5 2.5 2.5 2.5-2.5" /></>,
  }
  return (
    <svg aria-hidden="true" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">
      {paths[name]}
    </svg>
  )
}

function initialModule() {
  const candidate = window.location.hash.replace(/^#/, '')
  return MODULE_KEYS.has(candidate) ? candidate : 'today'
}

function KmfaHome() {
  const [activeKey, setActiveKey] = useState(initialModule)
  const [systemState, setSystemState] = useState('checking')
  const active = MODULES.find((item) => item.key === activeKey) ?? MODULES[0]

  useEffect(() => {
    const onHashChange = () => setActiveKey(initialModule())
    window.addEventListener('hashchange', onHashChange)
    return () => window.removeEventListener('hashchange', onHashChange)
  }, [])

  useEffect(() => {
    let live = true
    const controller = new AbortController()
    const timeout = window.setTimeout(() => controller.abort(), 5000)

    fetch('/healthz', {
      cache: 'no-store',
      credentials: 'omit',
      headers: { Accept: 'application/json' },
      signal: controller.signal,
    })
      .then((response) => {
        if (!response.ok) throw new Error(`health ${response.status}`)
        return response.json()
      })
      .then((body) => {
        if (!body || body.status !== 'ok') throw new Error('health payload')
        if (live) setSystemState('online')
      })
      .catch(() => {
        if (live) setSystemState('degraded')
      })
      .finally(() => window.clearTimeout(timeout))

    return () => {
      live = false
      controller.abort()
      window.clearTimeout(timeout)
    }
  }, [])

  const openModule = (key, { scroll = false } = {}) => {
    setActiveKey(key)
    window.history.replaceState(null, '', `#${key}`)
    if (scroll) {
      window.requestAnimationFrame(() => {
        document.getElementById('module-detail')?.scrollIntoView({ behavior: 'smooth', block: 'start' })
      })
    }
  }

  const healthCopy = {
    checking: ['正在确认', '公共入口已显示，正在检查基础服务。'],
    online: ['基础服务在线', '浅健康检查通过；功能可用性仍以各入口标注为准。'],
    degraded: ['基础服务暂不可确认', '导航与公开说明仍可使用；页面没有丢失或伪造数据。请稍后刷新。'],
  }[systemState]

  return (
    <div className="public-shell" data-shell-ready="true" data-system-state={systemState}>
      <a className="public-skip-link" href="#main-content">跳到主要内容</a>
      <header className="public-header">
        <a className="public-brand" href="/" aria-label="KMFA 首页">
          <span className="public-brand-mark">KM</span>
          <span>KMFA <small>BUSINESS COCKPIT</small></span>
        </a>
        <nav className="public-nav" aria-label="主要功能">
          {MODULES.map((item) => (
            <a
              key={item.key}
              href={`#${item.key}`}
              data-shell-nav={item.key}
              aria-current={activeKey === item.key ? 'location' : undefined}
              onClick={(event) => {
                event.preventDefault()
                openModule(item.key, { scroll: true })
              }}
            >
              {item.title}
            </a>
          ))}
        </nav>
        <a
          className={`public-health-chip is-${systemState}`}
          href="#system-status"
          aria-label={`系统状态：${healthCopy[0]}`}
        >
          <span aria-hidden="true" />{healthCopy[0]}
        </a>
      </header>

      <main id="main-content" tabIndex="-1">
        <section className="public-hero" aria-labelledby="hero-title">
          <div className="public-hero-copy">
            <p className="public-kicker"><span>KMFA</span> · BUSINESS COCKPIT</p>
            <h1 id="hero-title">把钱、票、成本与拍板，放进同一块驾驶舱。</h1>
            <p className="public-hero-lead">
              KMFA 是一套经营驾驶舱系统:回款、开票、成本、决策与报告在同一条四层可验证链路上运转。
              真数据、全留痕、可回溯;经营数据默认私有,公开页只讲能力、不露数字。
            </p>
            <div className="public-hero-actions">
              <a className="public-primary-action" href="/ops/app">进入经营驾驶舱</a>
              <a className="public-secondary-action" href="#capabilities">查看能力模块</a>
            </div>
          </div>
          <aside className="public-hero-index" aria-label="KMFA 三条原则">
            <p>KMFA / 00</p>
            <ol>
              <li><span>01</span> 真数据,不用演示冒充</li>
              <li><span>02</span> 每次拍板,全程留痕</li>
              <li><span>03</span> 经营数据,默认私有</li>
            </ol>
          </aside>
        </section>

        <div className="public-trust-strip" role="list" aria-label="系统底线">
          <span role="listitem">真数据接入</span>
          <span role="listitem">四层可验证链</span>
          <span role="listitem">决策留痕可回溯</span>
          <span role="listitem">经营数据默认私有</span>
        </div>

        <section className="public-capabilities" id="capabilities" aria-labelledby="capabilities-title">
          <div className="public-section-heading">
            <div>
              <p className="public-kicker">SIX MODULES, ONE COCKPIT</p>
              <h2 id="capabilities-title">六个模块,管住经营的每一步</h2>
            </div>
            <p>这六个模块已在驾驶舱内上线运转。公开页只介绍能力与边界;真实经营数字属于企业私有,只在授权的驾驶舱内可见。</p>
          </div>

          <div className="public-module-grid">
            {MODULES.map((item) => (
              <button
                className="public-module-card"
                type="button"
                key={item.key}
                data-shell-entry={item.key}
                aria-pressed={activeKey === item.key}
                aria-controls="module-detail"
                aria-label={`${item.title}：${item.status}`}
                onClick={() => openModule(item.key)}
              >
                <span className="public-card-code">{item.code}</span>
                <span className="public-card-icon"><Icon name={item.key} /></span>
                <span className="public-card-eyebrow">{item.eyebrow}</span>
                <strong>{item.title}</strong>
                <span className="public-card-summary">{item.summary}</span>
                <span className="public-card-footer">
                  <span>{item.status}</span><span aria-hidden="true">↗</span>
                </span>
              </button>
            ))}
          </div>
        </section>

        <section
          className="public-module-detail"
          id="module-detail"
          data-active-module={active.key}
          aria-live="polite"
          tabIndex="-1"
        >
          <div className="public-detail-label">
            <Icon name={active.key} />
            <span>{active.code} / {active.eyebrow}</span>
          </div>
          <div className="public-detail-copy">
            <p className="public-detail-state">{active.status}</p>
            <h2>{active.title}</h2>
            <p>{active.detail}</p>
          </div>
          <ul className="public-detail-facts">
            {active.facts.map((fact) => <li key={fact}>{fact}</li>)}
          </ul>
        </section>

        <section className="public-chain" id="chain" aria-labelledby="chain-title">
          <div className="public-section-heading">
            <div>
              <p className="public-kicker">VERIFIABLE CHAIN</p>
              <h2 id="chain-title">四层链:每个数字都讲得出来历</h2>
            </div>
            <p>从事实底账到最终拍板,四层依次咬合;任何一步重算,旧版本全保留。这是 KMFA 与"随手 Excel"的根本区别。</p>
          </div>
          <ol className="public-chain-steps">
            {CHAIN_STEPS.map((step) => (
              <li key={step.num}>
                <span aria-hidden="true">{step.num}</span>
                <strong>{step.title}</strong>
                <p>{step.text}</p>
              </li>
            ))}
          </ol>
        </section>

        <section className="public-workspace-teaser" aria-labelledby="workspace-title">
          <div>
            <p className="public-kicker">OPEN SLICE</p>
            <h2 id="workspace-title">一个公开可试的工程切片</h2>
            <p>
              匿名工作区是 KMFA 工程质量的公开样片:无需账号即可创建可恢复的服务器工作区、上传文件、保存进度。
              它与经营数据完全隔离,试的是工程,不碰你的账。
            </p>
          </div>
          <a className="public-secondary-action" href="/workspace">打开公开工作区</a>
        </section>

        <section className="public-system" id="system-status" aria-labelledby="system-title">
          <div className="public-section-heading">
            <div>
              <p className="public-kicker">EXPLICIT STATES</p>
              <h2 id="system-title">系统状态</h2>
            </div>
            <p>基础依赖失败时，导航和边界说明仍然保留；不会用空白页面或虚构数据代替错误。</p>
          </div>
          <div
            className={`public-system-card is-${systemState}`}
            role="status"
            aria-live="polite"
            aria-atomic="true"
          >
            <span className="public-system-light" aria-hidden="true" />
            <div>
              <strong>{healthCopy[0]}</strong>
              <p>{healthCopy[1]}</p>
            </div>
            <code>{systemState}</code>
          </div>
        </section>

        <section className="public-boundary" aria-labelledby="boundary-title">
          <p className="public-kicker">PUBLIC SOFTWARE, PRIVATE NUMBERS</p>
          <h2 id="boundary-title">公开的是软件与能力，不是经营数据。</h2>
          <p>驾驶舱里的回款、开票、成本与决策属于企业私有。公开站点只呈现产品能力与工程质量,未经明确公开的数字不会出现在这里。</p>
          <a href="#chain">了解四层可验证链</a>
        </section>
      </main>

      <footer className="public-footer">
        <span>KMFA</span>
        <p>经营驾驶舱 · 真数据 · 全留痕 · 经营数据默认私有</p>
        <a href="#main-content">回到顶部</a>
      </footer>
    </div>
  )
}

export default KmfaHome
