import React, { useEffect, useMemo, useState } from 'react'

const API_BASE = '/public-api/walking-skeleton/v1'

const ERROR_COPY = {
  walking_skeleton_disabled: '早期骨架当前处于安全回滚状态。已有服务器状态不会因此删除。',
  walking_skeleton_storage_unavailable: '服务器耐久存储暂不可用，未执行本次操作。',
  workspace_not_found: '工作区不存在、会话已过期，或当前会话无权访问。请使用恢复码重新恢复。',
  recovery_not_found: '恢复码无效。请核对完整恢复码；平台无法通过邮箱代找回。',
  invalid_project_name: '项目名不能为空，也不能包含控制字符。',
  invalid_filename: '文件名无效。请选择不含路径或控制字符的文件。',
  artifact_too_large: '该早期骨架单文件上限为 8 MiB；文件未写入。',
  artifact_limit_reached: '该早期骨架每个工作区只验证一个文件，已有文件不会被覆盖。',
  artifact_integrity_failed: '下载完整性校验失败，服务器已阻止返回损坏字节。',
  artifact_unavailable: '文件当前不可读取，服务器没有返回替代或伪造内容。',
}

async function errorFromResponse(response) {
  let code = ''
  try {
    const body = await response.json()
    code = typeof body.detail === 'string' ? body.detail : ''
  } catch {
    code = ''
  }
  const error = new Error(ERROR_COPY[code] || `操作未完成（HTTP ${response.status}）。`)
  error.code = code
  return error
}

async function jsonRequest(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    cache: 'no-store',
    credentials: 'omit',
    ...options,
    headers: {
      Accept: 'application/json',
      ...(options.headers || {}),
    },
  })
  if (!response.ok) throw await errorFromResponse(response)
  return response.json()
}

function formatBytes(value) {
  if (!Number.isFinite(value)) return '—'
  if (value < 1024) return `${value} B`
  return `${(value / 1024).toFixed(value < 1024 * 100 ? 1 : 0)} KiB`
}

async function sha256Hex(blob) {
  const digest = await window.crypto.subtle.digest('SHA-256', await blob.arrayBuffer())
  return Array.from(new Uint8Array(digest), (byte) => byte.toString(16).padStart(2, '0')).join('')
}

function SkeletonBoundary({ state, retry }) {
  const copy = {
    checking: ['正在确认早期骨架', '公共主页已可用；正在读取服务器功能开关与存储健康状态。'],
    rollback: ['早期骨架已安全回滚', '创建、恢复、上传与下载已关闭；公共主页保持可用，既有服务器状态不会被 Flag 删除。'],
    unavailable: ['早期骨架暂不可确认', '没有把失败显示成成功，也没有退回浏览器临时存储。稍后可重新检查。'],
  }[state]

  return (
    <div className={`walking-state walking-state-${state}`} data-walking-boundary={state}>
      <p className="walking-state-label">{state.toUpperCase()}</p>
      <h3>{copy[0]}</h3>
      <p>{copy[1]}</p>
      {state === 'unavailable' && <button type="button" onClick={retry}>重新检查</button>}
    </div>
  )
}

function WalkingSkeleton() {
  const [availability, setAvailability] = useState('checking')
  const [limits, setLimits] = useState({ maxBytes: 8 * 1024 * 1024, maxArtifacts: 1 })
  const [mode, setMode] = useState('create')
  const [projectName, setProjectName] = useState('')
  const [recoveryInput, setRecoveryInput] = useState('')
  const [recoveryCode, setRecoveryCode] = useState('')
  const [session, setSession] = useState(null)
  const [selectedFile, setSelectedFile] = useState(null)
  const [busy, setBusy] = useState(false)
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')
  const [statusAttempt, setStatusAttempt] = useState(0)

  useEffect(() => {
    let live = true
    const controller = new AbortController()
    const timeout = window.setTimeout(() => controller.abort(), 5000)
    setAvailability('checking')
    jsonRequest('/status', { signal: controller.signal })
      .then((status) => {
        if (!live) return
        if (!status.enabled) {
          setAvailability('rollback')
          return
        }
        setLimits({
          maxBytes: status.limits?.max_bytes || 8 * 1024 * 1024,
          maxArtifacts: status.limits?.max_artifacts || 1,
        })
        setAvailability(status.healthy ? 'ready' : 'unavailable')
      })
      .catch(() => {
        if (live) setAvailability('unavailable')
      })
      .finally(() => window.clearTimeout(timeout))
    return () => {
      live = false
      controller.abort()
      window.clearTimeout(timeout)
    }
  }, [statusAttempt])

  const workspace = session?.workspace || null
  const bearer = session ? { Authorization: `Bearer ${session.accessToken}` } : {}
  const artifact = workspace?.artifact || null
  const progress = workspace?.progress ?? 0
  const progressText = useMemo(() => `${progress}%`, [progress])

  const resetFeedback = () => {
    setMessage('')
    setError('')
  }

  const run = async (operation) => {
    resetFeedback()
    setBusy(true)
    try {
      await operation()
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : '操作未完成。')
    } finally {
      setBusy(false)
    }
  }

  const createWorkspace = (event) => {
    event.preventDefault()
    run(async () => {
      const result = await jsonRequest('/workspaces', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ project_name: projectName }),
      })
      setSession({
        workspace: result.workspace,
        accessToken: result.access_token,
        expiresAt: result.access_expires_at,
      })
      setRecoveryCode(result.recovery_code)
      setProjectName(result.workspace.project_name)
      setMessage('工作区已写入服务器。请先离线保存下方恢复码；刷新页面后本页会话不会保留。')
    })
  }

  const recoverWorkspace = (event) => {
    event.preventDefault()
    run(async () => {
      const result = await jsonRequest('/recoveries', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ recovery_code: recoveryInput.trim() }),
      })
      setSession({
        workspace: result.workspace,
        accessToken: result.access_token,
        expiresAt: result.access_expires_at,
      })
      setRecoveryCode('')
      setRecoveryInput('')
      setProjectName(result.workspace.project_name)
      setMessage('已从服务器恢复工作区，并签发新的短时会话。')
    })
  }

  const saveWorkspace = (event) => {
    event.preventDefault()
    const form = new FormData(event.currentTarget)
    run(async () => {
      const result = await jsonRequest(`/workspaces/${workspace.workspace_id}`, {
        method: 'PATCH',
        headers: { ...bearer, 'Content-Type': 'application/json' },
        body: JSON.stringify({
          project_name: String(form.get('project_name') || ''),
          progress: Number(form.get('progress')),
        }),
      })
      setSession((current) => ({ ...current, workspace: result }))
      setProjectName(result.project_name)
      setMessage(`项目与进度已写入服务器：${result.progress}%。`)
    })
  }

  const uploadArtifact = (event) => {
    event.preventDefault()
    const form = event.currentTarget
    if (!selectedFile) {
      setError('请先选择一个文件。')
      return
    }
    if (selectedFile.size > limits.maxBytes) {
      setError(`文件超过当前早期骨架上限 ${formatBytes(limits.maxBytes)}；未开始上传。`)
      return
    }
    run(async () => {
      const response = await fetch(`${API_BASE}/workspaces/${workspace.workspace_id}/artifact`, {
        method: 'PUT',
        cache: 'no-store',
        credentials: 'omit',
        headers: {
          Accept: 'application/json',
          ...bearer,
          'Content-Type': selectedFile.type || 'application/octet-stream',
          'X-KMFA-Filename': encodeURIComponent(selectedFile.name),
        },
        body: selectedFile,
      })
      if (!response.ok) throw await errorFromResponse(response)
      const result = await response.json()
      setSession((current) => ({ ...current, workspace: result }))
      setSelectedFile(null)
      form.reset()
      setMessage(`文件已按 attachment-only 模式写入服务器，SHA-256：${result.artifact.sha256}`)
    })
  }

  const downloadArtifact = () => {
    run(async () => {
      const response = await fetch(
        `${API_BASE}/workspaces/${workspace.workspace_id}/artifact/download`,
        {
          method: 'POST',
          cache: 'no-store',
          credentials: 'omit',
          headers: { ...bearer },
        },
      )
      if (!response.ok) throw await errorFromResponse(response)
      const serverHash = response.headers.get('X-KMFA-Artifact-SHA256') || ''
      if (serverHash !== artifact.sha256) throw new Error('下载响应 hash 与项目记录不一致，已停止保存。')
      const blob = await response.blob()
      const browserHash = await sha256Hex(blob)
      if (browserHash !== serverHash) throw new Error('浏览器下载字节的 SHA-256 不一致，已停止保存。')
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = artifact.name
      document.body.appendChild(link)
      link.click()
      link.remove()
      window.setTimeout(() => URL.revokeObjectURL(url), 1000)
      setMessage(`下载已发起；浏览器与服务器 SHA-256 一致：${browserHash}`)
    })
  }

  const clearPageSession = () => {
    setSession(null)
    setRecoveryCode('')
    setRecoveryInput('')
    setProjectName('')
    setSelectedFile(null)
    setMode('recover')
    setMessage('本页短时会话已清除，服务器工作区和文件未删除。请使用恢复码重新进入。')
    setError('')
  }

  return (
    <section
      className="public-walking"
      id="walking-skeleton"
      aria-labelledby="walking-title"
      data-walking-skeleton-state={availability}
    >
      <div className="walking-heading">
        <div>
          <p className="public-kicker"><span>EARLY / FLAGGED</span> · TEST-QA-001</p>
          <h2 id="walking-title">第一个真实、可恢复的文件旅程</h2>
        </div>
        <p>
          这是 S03 Walking Skeleton，不是 GA：只验证一个工作区、一个任意类型文件、项目进度、服务器重启恢复与 hash 下载。
          完整对象存储、备份演练、扫描、反滥用、多文件和明确删除将在 S04–S07 硬化。
        </p>
      </div>

      {availability !== 'ready' ? (
        <SkeletonBoundary state={availability} retry={() => setStatusAttempt((value) => value + 1)} />
      ) : (
        <div className="walking-console" data-walking-ready="true">
          {!session ? (
            <div className="walking-entry">
              <div className="walking-mode-switch" role="group" aria-label="工作区进入方式">
                <button
                  type="button"
                  aria-pressed={mode === 'create'}
                  onClick={() => { resetFeedback(); setMode('create') }}
                >
                  创建工作区
                </button>
                <button
                  type="button"
                  aria-pressed={mode === 'recover'}
                  onClick={() => { resetFeedback(); setMode('recover') }}
                >
                  使用恢复码
                </button>
              </div>

              {mode === 'create' ? (
                <form className="walking-form" data-walking-create="true" onSubmit={createWorkspace}>
                  <label htmlFor="walking-project-create">项目名称</label>
                  <input
                    id="walking-project-create"
                    value={projectName}
                    onChange={(event) => setProjectName(event.target.value)}
                    maxLength="120"
                    required
                    autoComplete="off"
                    placeholder="例如：我的第一个 KMFA 项目"
                  />
                  <button type="submit" disabled={busy}>创建并生成恢复码</button>
                  <p>不要求账号、邮箱或 OAuth。恢复码只显示一次；平台不能通过邮箱找回。</p>
                </form>
              ) : (
                <form className="walking-form" data-walking-recover="true" onSubmit={recoverWorkspace}>
                  <label htmlFor="walking-recovery-code">恢复码</label>
                  <textarea
                    id="walking-recovery-code"
                    value={recoveryInput}
                    onChange={(event) => setRecoveryInput(event.target.value)}
                    rows="3"
                    required
                    autoComplete="off"
                    spellCheck="false"
                    placeholder="kmfa-r1-…"
                  />
                  <button type="submit" disabled={busy}>恢复服务器工作区</button>
                  <p>恢复材料不进入 URL、localStorage 或第三方登录流程。</p>
                </form>
              )}
            </div>
          ) : (
            <div className="walking-workspace" data-workspace-ready="true">
              <div className="walking-workspace-head">
                <div>
                  <p className="walking-state-label">SERVER WORKSPACE</p>
                  <h3>{workspace.project_name}</h3>
                  <p>短时会话到期：{session.expiresAt}</p>
                </div>
                <button type="button" className="walking-quiet" onClick={clearPageSession}>清除本页会话</button>
              </div>

              {recoveryCode && (
                <div className="walking-recovery" data-recovery-code="visible-once">
                  <strong>现在保存恢复码</strong>
                  <code data-recovery-code-value="true">{recoveryCode}</code>
                  <p>它等同于当前工作区的恢复能力。本阶段尚未实现 `.kmfa-recovery` 文件、轮换或撤销；不要分享，也不要放进 URL。</p>
                </div>
              )}

              <div className="walking-grid">
                <form className="walking-card walking-form" data-walking-save="true" onSubmit={saveWorkspace}>
                  <p className="walking-card-code">01 / PROJECT + PROGRESS</p>
                  <label htmlFor="walking-project-save">项目名称</label>
                  <input
                    id="walking-project-save"
                    name="project_name"
                    value={projectName}
                    onChange={(event) => setProjectName(event.target.value)}
                    maxLength="120"
                    required
                  />
                  <label htmlFor="walking-progress">项目进度：{progressText}</label>
                  <input
                    id="walking-progress"
                    name="progress"
                    type="range"
                    min="0"
                    max="100"
                    value={progress}
                    onChange={(event) => {
                      const next = Number(event.target.value)
                      setSession((current) => ({
                        ...current,
                        workspace: { ...current.workspace, progress: next },
                      }))
                    }}
                  />
                  <button type="submit" disabled={busy}>保存项目与进度</button>
                </form>

                <form className="walking-card walking-form" data-walking-upload="true" onSubmit={uploadArtifact}>
                  <p className="walking-card-code">02 / PRIVATE ARTIFACT</p>
                  <label htmlFor="walking-file">选择一个任意类型文件</label>
                  <input
                    id="walking-file"
                    type="file"
                    onChange={(event) => setSelectedFile(event.target.files?.[0] || null)}
                    disabled={Boolean(artifact)}
                  />
                  <p>
                    上限 {formatBytes(limits.maxBytes)}，最多 {limits.maxArtifacts} 个。未知或危险扩展名只存储、只按附件下载，不执行、不预览。
                  </p>
                  <button type="submit" disabled={busy || Boolean(artifact)}>
                    {artifact ? '已保存一个文件' : '上传到服务器'}
                  </button>
                </form>

                <div className="walking-card walking-artifact" data-walking-artifact={artifact ? 'ready' : 'empty'}>
                  <p className="walking-card-code">03 / VERIFY + DOWNLOAD</p>
                  {artifact ? (
                    <>
                      <h4>{artifact.name}</h4>
                      <dl>
                        <div><dt>字节</dt><dd>{artifact.size_bytes}</dd></div>
                        <div><dt>模式</dt><dd>attachment-only</dd></div>
                        <div><dt>SHA-256</dt><dd><code>{artifact.sha256}</code></dd></div>
                      </dl>
                      <button type="button" data-walking-download="true" onClick={downloadArtifact} disabled={busy}>校验并下载</button>
                    </>
                  ) : (
                    <p>上传后显示服务器记录的字节数与 SHA-256；空状态不会生成样例成功。</p>
                  )}
                </div>
              </div>
            </div>
          )}

          <div className="walking-feedback" aria-live="polite" aria-atomic="true">
            {message && <p data-walking-message="success">{message}</p>}
            {error && <p className="is-error" data-walking-message="error">{error}</p>}
          </div>
        </div>
      )}

      <div className="walking-contract" role="list" aria-label="早期骨架边界">
        <span role="listitem">服务器状态，不用 localStorage</span>
        <span role="listitem">恢复码服务端只存 hash</span>
        <span role="listitem">文件不进入静态公开目录</span>
        <span role="listitem">Flag 回滚不删已有状态</span>
      </div>
    </section>
  )
}

export default WalkingSkeleton
