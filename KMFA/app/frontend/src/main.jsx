import React from 'react'
import { createRoot } from 'react-dom/client'

class VisibleErrorBoundary extends React.Component {
  constructor(props) {
    super(props)
    this.state = { failed: false }
  }

  static getDerivedStateFromError() {
    return { failed: true }
  }

  componentDidCatch(error) {
    console.error('KMFA interface render failed', error)
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
  .catch((error) => {
    console.error('KMFA interface module failed to load', error)
    const status = document.getElementById('static-runtime-status')
    if (status) {
      status.dataset.jsState = 'load-error'
      status.textContent = '增强界面加载失败；静态公共入口仍可使用。刷新重试。'
    }
  })
