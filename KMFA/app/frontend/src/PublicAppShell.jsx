import React, { useEffect, useMemo, useState } from 'react'
import './public-shell.css'

const MODULES = [
  {
    key: 'project',
    code: '01',
    title: '项目',
    eyebrow: 'PROJECTS',
    status: '入口可达',
    summary: '进入项目容器，统一查看文件、进度与可验证结果。',
    detail: '当前阶段交付公共导航壳，尚未创建或保存任何项目。匿名工作区接入后，这里会成为项目的真实入口。',
    facts: ['不要求账号、邮箱或 OAuth', '当前不会写入浏览器存储', '未接入前不展示虚构项目'],
  },
  {
    key: 'upload',
    code: '02',
    title: '上传',
    eyebrow: 'FILES',
    status: '入口可达',
    summary: '从一个明确入口提交文件，并看见真实处理状态。',
    detail: '安全文件通道尚未接入。当前页面不会读取、接受或传输你选择的文件，也不会用演示成功掩盖缺失能力。',
    facts: ['任意文件支持将在后续阶段接入', '接入前不显示文件选择器', '失败时必须保留清晰、可恢复的状态'],
  },
  {
    key: 'search',
    code: '03',
    title: '搜索',
    eyebrow: 'SEARCH',
    status: '公开说明可搜',
    summary: '定位项目、文件与报告；当前先支持本页公开说明检索。',
    detail: '下方搜索只检索这张公共页面的功能说明，不会查询工作区、文件名或任何未主动公开的数据。',
    facts: ['搜索范围会始终明确标注', '当前不连接私有数据源', '没有结果时明确返回空状态'],
  },
  {
    key: 'progress',
    code: '04',
    title: '进度',
    eyebrow: 'PROGRESS',
    status: '接线状态可见',
    summary: '区分已经可用、正在接入与尚未验证的能力。',
    detail: '这里显示的是软件能力接入状态，不是你的项目进度。目前仅确认公共入口与导航已接通。',
    facts: ['公共入口：已接通', '匿名工作区：待接入', '长期持久化与恢复：待验证'],
  },
  {
    key: 'report',
    code: '05',
    title: '报告',
    eyebrow: 'REPORTS',
    status: '明确空状态',
    summary: '只呈现用户明确生成或主动公开的报告。',
    detail: '当前没有可公开报告。站点公开不代表用户内容公开；未主动公开的项目、文件和结果不会出现在这里。',
    facts: ['不展示历史私有经营数据', '不以样例冒充真实报告', '导出能力接入后会提供可验证下载'],
  },
  {
    key: 'help',
    code: '06',
    title: '帮助',
    eyebrow: 'HELP',
    status: '说明可用',
    summary: '先讲清能力边界，再给出下一步与故障处理。',
    detail: 'KMFA 的公开使用路径不设账号前置。每个能力会如实标注接入状态；如果关键依赖不可用，页面仍保留导航与说明。',
    facts: ['无需注册即可进入', '依赖故障不会显示空白页', '数据仅在用户明确删除时删除是后续持久化验收目标'],
  },
]

const MODULE_KEYS = new Set(MODULES.map((item) => item.key))

function Icon({ name }) {
  const paths = {
    project: <><path d="M3.5 6.5h6l1.6 2h9.4v10h-17z"/><path d="M3.5 6.5v-2h6l1.5 2"/></>,
    upload: <><path d="M12 16V4"/><path d="m7.5 8.5 4.5-4.5 4.5 4.5"/><path d="M4 15.5v4h16v-4"/></>,
    search: <><circle cx="10.5" cy="10.5" r="6.5"/><path d="m15.3 15.3 4.2 4.2"/></>,
    progress: <><path d="M4 19V9"/><path d="M10 19V4"/><path d="M16 19v-7"/><path d="M22 19H2"/></>,
    report: <><path d="M5 3.5h10l4 4v13H5z"/><path d="M15 3.5v4h4"/><path d="M8.5 12h7M8.5 16h5"/></>,
    help: <><circle cx="12" cy="12" r="9"/><path d="M9.8 9a2.4 2.4 0 1 1 3 2.3c-.8.3-.8.9-.8 1.7"/><path d="M12 17h.01"/></>,
  }
  return (
    <svg aria-hidden="true" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">
      {paths[name]}
    </svg>
  )
}

function initialModule() {
  const candidate = window.location.hash.replace(/^#/, '')
  return MODULE_KEYS.has(candidate) ? candidate : 'project'
}

function PublicAppShell() {
  const [activeKey, setActiveKey] = useState(initialModule)
  const [systemState, setSystemState] = useState('checking')
  const [query, setQuery] = useState('')
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

  const searchResults = useMemo(() => {
    const term = query.trim().toLocaleLowerCase('zh-CN')
    if (!term) return []
    return MODULES.filter((item) => (
      [item.title, item.eyebrow, item.summary, item.detail, ...item.facts]
        .join(' ')
        .toLocaleLowerCase('zh-CN')
        .includes(term)
    ))
  }, [query])

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
          <span>KMFA <small>PUBLIC WORKSPACE</small></span>
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
            <p className="public-kicker"><span>NO ACCOUNT</span> · ONE PUBLIC ENTRY</p>
            <h1 id="hero-title">一个入口，通往项目、文件与可验证进度。</h1>
            <p className="public-hero-lead">
              根域名就是主页。无需账号即可进入；每项能力按真实接入状态开放，未主动公开的数据不会因为站点公开而公开。
            </p>
            <div className="public-hero-actions">
              <a className="public-primary-action" href="#capabilities">查看功能入口</a>
              <a className="public-secondary-action" href="#system-status">查看系统状态</a>
            </div>
          </div>
          <aside className="public-hero-index" aria-label="公共入口原则">
            <p>PUBLIC / 00</p>
            <ol>
              <li><span>01</span> 不设注册前置</li>
              <li><span>02</span> 不把私有内容公开</li>
              <li><span>03</span> 不以演示冒充完成</li>
            </ol>
          </aside>
        </section>

        <div className="public-trust-strip" role="list" aria-label="使用边界">
          <span role="listitem">无需账号</span>
          <span role="listitem">状态透明</span>
          <span role="listitem">故障不空白</span>
          <span role="listitem">删除由用户明确触发</span>
        </div>

        <section className="public-capabilities" id="capabilities" aria-labelledby="capabilities-title">
          <div className="public-section-heading">
            <div>
              <p className="public-kicker">SIX OPERABLE ENTRIES</p>
              <h2 id="capabilities-title">从这里开始</h2>
            </div>
            <p>选择任一入口即可查看当前能力与边界。入口可操作，不代表尚未接入的底层能力已经完成。</p>
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

          {active.key === 'search' && (
            <form className="public-search" onSubmit={(event) => event.preventDefault()} role="search">
              <label htmlFor="public-search-input">搜索本页公开说明</label>
              <div>
                <input
                  id="public-search-input"
                  data-public-search="true"
                  type="search"
                  value={query}
                  onChange={(event) => setQuery(event.target.value)}
                  placeholder="例如：上传、恢复、报告"
                  autoComplete="off"
                />
                <button type="submit">检索</button>
              </div>
              <p className="public-search-scope">范围：仅本页六项公开说明，不查询用户工作区。</p>
              {query.trim() && (
                <div
                  className="public-search-results"
                  data-search-results="true"
                  role="region"
                  aria-live="polite"
                  aria-label="公开说明搜索结果"
                >
                  {searchResults.length ? (
                    <ul>
                      {searchResults.map((item) => (
                        <li key={item.key}>
                          <button type="button" onClick={() => openModule(item.key)}>{item.title}</button>
                          <span>{item.summary}</span>
                        </li>
                      ))}
                    </ul>
                  ) : <p>没有匹配的公开说明。工作区搜索尚未接入。</p>}
                </div>
              )}
            </form>
          )}
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
          <p className="public-kicker">PUBLIC SOFTWARE, PRIVATE CONTENT</p>
          <h2 id="boundary-title">公开的是软件入口，不是你的内容。</h2>
          <p>项目、文件、分数与报告必须由用户在匿名工作区中明确创建或公开。当前公共壳不读取既有私有 API，也不展示历史经营数据。</p>
          <a href="#help" onClick={(event) => { event.preventDefault(); openModule('help', { scroll: true }) }}>查看帮助与边界说明</a>
        </section>
      </main>

      <footer className="public-footer">
        <span>KMFA</span>
        <p>公开入口 · 匿名可达 · 能力按验证状态开放</p>
        <a href="#main-content">回到顶部</a>
      </footer>
    </div>
  )
}

export default PublicAppShell
