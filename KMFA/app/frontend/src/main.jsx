import React from 'react'
import { createRoot } from 'react-dom/client'

const REDACTED_DIAGNOSTIC = '[REDACTED_KMFA_CAPABILITY]'
const CAPABILITY_PATTERN = /\bkmfa-(?:r1|a1)-[A-Za-z0-9_-]{20,128}\b/
const BEARER_PATTERN = /\bBearer\s+[A-Za-z0-9._~+/=-]{16,2048}/gi

function containsCapability(value) {
  let candidate = value
  for (let attempt = 0; attempt < 5; attempt += 1) {
    if (CAPABILITY_PATTERN.test(candidate)) return true
    try {
      const decoded = decodeURIComponent(candidate)
      if (decoded === candidate) return false
      candidate = decoded
    } catch {
      return false
    }
  }
  return CAPABILITY_PATTERN.test(candidate)
}

function redactBrowserDiagnostic(value) {
  try {
    const text = value instanceof Error ? `${value.name}: ${value.message}` : String(value)
    if (containsCapability(text)) return REDACTED_DIAGNOSTIC
    return text.replace(BEARER_PATTERN, `Bearer ${REDACTED_DIAGNOSTIC}`)
  } catch {
    return '[REDACTED_KMFA_DIAGNOSTIC]'
  }
}

// React and browser libraries can log before an ErrorBoundary callback. Keep a
// process-wide browser console filter so no diagnostic level forwards raw
// capability-bearing Error objects or structured metadata.
for (const level of ['debug', 'info', 'log', 'warn', 'error']) {
  const original = window.console[level].bind(window.console)
  window.console[level] = (...values) => original(...values.map(redactBrowserDiagnostic))
}

class VisibleErrorBoundary extends React.Component {
  constructor(props) {
    super(props)
    this.state = { failed: false }
  }

  static getDerivedStateFromError() {
    return { failed: true }
  }

  componentDidCatch() {
    // Never forward raw Error objects: request bodies and capability-bearing
    // values may be present in a browser exception's causal chain.
    console.error('KMFA_UI_RENDER_ERROR')
  }

  render() {
    if (this.state.failed) {
      return (
        <main className="public-runtime-error" data-runtime-state="render-error" role="alert">
          <p>KMFA</p>
          <h1>界面暂时无法完成加载</h1>
          <p>公开入口仍然可达，但增强界面发生错误。刷新重试；你的数据没有因此被删除或公开。</p>
          <button type="button" onClick={() => window.location.reload()}>刷新页面</button>
        </main>
      )
    }
    return this.props.children
  }
}

const root = document.getElementById('root')
const isPrivateOperationsApp = window.location.pathname === '/ops/app'
  || window.location.pathname.startsWith('/ops/app/')

function loadPrivateOperationsApp() {
  return import('./App.jsx')
}

function loadPublicAppShell() {
  return import('./PublicAppShell.jsx')
}

const appModule = isPrivateOperationsApp ? loadPrivateOperationsApp() : loadPublicAppShell()

appModule
  .then(({ default: App }) => {
    createRoot(root).render(<VisibleErrorBoundary><App /></VisibleErrorBoundary>)
  })
  .catch(() => {
    console.error('KMFA_UI_MODULE_LOAD_ERROR')
    const status = document.getElementById('static-runtime-status')
    if (status) {
      status.dataset.jsState = 'load-error'
      status.textContent = '增强界面加载失败；静态公共入口仍可使用。刷新重试。'
    }
  })
