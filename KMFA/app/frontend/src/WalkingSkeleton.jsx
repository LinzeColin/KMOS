import React, { useEffect, useMemo, useState } from 'react'

const API_BASE = '/public-api/walking-skeleton/v1'
const RECOVERY_FILE_MEDIA_TYPE = 'application/vnd.kmfa.recovery+json'
const MAX_RECOVERY_FILE_BYTES = 4096

const ERROR_COPY = {
  walking_skeleton_disabled: '早期骨架当前处于安全回滚状态。已有服务器状态不会因此删除。',
  walking_skeleton_storage_unavailable: '服务器耐久存储暂不可用，未执行本次操作。',
  workspace_not_found: '工作区不存在、会话已过期，或当前会话无权访问。请使用恢复码重新恢复。',
  recovery_not_found: '恢复码或恢复文件无效、已截断或已被轮换撤销。平台无法通过邮箱代找回。',
  invalid_recovery_file: '文件不是 KMFA 恢复文件；未授予任何访问。',
  recovery_file_too_large: '恢复文件超过 4 KiB 安全上限；未读取或授予访问。',
  invalid_project_name: '项目名不能为空，也不能包含控制字符。',
  invalid_filename: '文件名无效。请选择不含路径或控制字符的文件。',
  artifact_too_large: '该早期骨架单文件上限为 8 MiB；文件未写入。',
  artifact_limit_reached: '该早期骨架每个工作区只验证一个文件，已有文件不会被覆盖。',
  artifact_integrity_failed: '下载完整性校验失败，服务器已阻止返回损坏字节。',
  artifact_unavailable: '文件当前不可读取，服务器没有返回替代或伪造内容。',
  workspace_capacity_reached: '当前匿名灰度容量已满；公共浏览仍可用，已有工作区没有被删除。',
  artifact_capacity_reached: '当前文件存储预算不足；本次文件未写入，已有文件没有被删除。',
  workspace_audit_capacity_reached: '该早期工作区已达到审计安全上限；本次变更未执行。',
  secret_in_url_rejected: '请求 URL 或来源页包含恢复材料，服务器已拒绝处理。请只通过受保护的表单正文提交。',
  cross_origin_session_request_rejected: '会话操作不是从 KMFA 同源页面发起，服务器已拒绝处理。',
  risk_capacity_limited: '匿名资源预算当前繁忙；公共浏览仍可使用，请按服务器提示稍后重试。',
  risk_challenge_required: '需要完成一次匿名安全校验后重试；不要求登录或提供个人资料。',
  risk_challenge_invalid: '匿名安全校验无效或已过期；未执行本次操作。',
  risk_challenge_replayed: '匿名安全校验已经使用，不能重放；未执行本次操作。',
  abuse_control_unavailable: '匿名资源保护暂不可用；昂贵操作已安全关闭，公共浏览保持可用。',
  abuse_policy_configuration_invalid: '匿名资源策略配置无效；昂贵操作已安全关闭。',
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

function leadingZeroBits(bytes) {
  let count = 0
  for (const byte of bytes) {
    if (byte === 0) {
      count += 8
      continue
    }
    count += 8 - byte.toString(2).length
    break
  }
  return count
}

async function solveRiskChallenge(challenge) {
  const token = typeof challenge?.token === 'string' ? challenge.token : ''
  const difficulty = Number(challenge?.difficulty_bits)
  if (
    challenge?.algorithm !== 'sha256-leading-zero-bits'
    || challenge?.proof_header !== 'X-KMFA-Challenge-Proof'
    || !/^[A-Za-z0-9_.-]{40,1600}$/.test(token)
    || !Number.isInteger(difficulty)
    || difficulty < 8
    || difficulty > 20
  ) {
    throw new Error(ERROR_COPY.risk_challenge_invalid)
  }
  const encoder = new TextEncoder()
  for (let nonce = 0; nonce <= 0xffffffff; nonce += 1) {
    const proof = `${token}:${nonce}`
    const digest = await window.crypto.subtle.digest('SHA-256', encoder.encode(proof))
    if (leadingZeroBits(new Uint8Array(digest)) >= difficulty) return proof
  }
  throw new Error(ERROR_COPY.risk_challenge_invalid)
}

async function fetchWithRiskChallenge(url, options = {}) {
  const response = await fetch(url, options)
  if (response.status !== 429) return response
  let payload = null
  try {
    payload = await response.clone().json()
  } catch {
    return response
  }
  if (payload?.detail !== 'risk_challenge_required' || !payload.challenge) {
    return response
  }
  const proof = await solveRiskChallenge(payload.challenge)
  return fetch(url, {
    ...options,
    headers: {
      ...(options.headers || {}),
      'X-KMFA-Challenge-Proof': proof,
    },
  })
}

async function jsonRequest(path, options = {}) {
  const response = await fetchWithRiskChallenge(`${API_BASE}${path}`, {
    cache: 'no-store',
    credentials: 'same-origin',
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

function saveBlob(blob, filename) {
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  link.remove()
  window.setTimeout(() => URL.revokeObjectURL(url), 1000)
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
  const [recoveryFile, setRecoveryFile] = useState(null)
  const [recoveryFileKey, setRecoveryFileKey] = useState(0)
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
        expiresAt: result.access_expires_at,
      })
      setRecoveryCode(result.recovery_code)
      setProjectName(result.workspace.project_name)
      setMessage('工作区已写入服务器，并签发可撤销的受保护短时会话。请先离线保存下方恢复码。')
    })
  }

  const recoverWorkspace = (event) => {
    event.preventDefault()
    const submittedRecovery = recoveryInput.trim()
    if (!submittedRecovery) {
      setError('请输入完整恢复码。')
      return
    }
    run(async () => {
      const result = await jsonRequest('/recoveries', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ recovery_code: submittedRecovery }),
      })
      setSession({
        workspace: result.workspace,
        expiresAt: result.access_expires_at,
      })
      setRecoveryCode(submittedRecovery)
      setRecoveryInput('')
      setProjectName(result.workspace.project_name)
      setMessage('已用恢复码恢复工作区并签发新的受保护短时会话；恢复码未被服务器回传。')
    })
  }

  const importRecoveryFile = () => {
    if (!recoveryFile) {
      setError('请选择一个 .kmfa-recovery 文件。')
      return
    }
    if (recoveryFile.size > MAX_RECOVERY_FILE_BYTES) {
      setError('恢复文件超过 4 KiB 安全上限；未开始上传。')
      return
    }
    run(async () => {
      const response = await fetchWithRiskChallenge(`${API_BASE}/recovery-files/import`, {
        method: 'POST',
        cache: 'no-store',
        credentials: 'same-origin',
        headers: {
          Accept: 'application/json',
          'Content-Type': RECOVERY_FILE_MEDIA_TYPE,
        },
        body: recoveryFile,
      })
      if (!response.ok) throw await errorFromResponse(response)
      const result = await response.json()
      setSession({
        workspace: result.workspace,
        expiresAt: result.access_expires_at,
      })
      setRecoveryCode('')
      setRecoveryInput('')
      setRecoveryFile(null)
      setRecoveryFileKey((value) => value + 1)
      setProjectName(result.workspace.project_name)
      setMessage('已用恢复文件恢复同一服务器工作区；服务端没有回传文件内的恢复密钥。')
    })
  }

  const downloadRecoveryFile = () => {
    if (!recoveryCode) {
      setError('当前页面没有恢复码明文。可保留已导入文件，或轮换生成新的恢复材料。')
      return
    }
    run(async () => {
      const response = await fetchWithRiskChallenge(
        `${API_BASE}/workspaces/${workspace.workspace_id}/recovery-file`,
        {
          method: 'POST',
          cache: 'no-store',
          credentials: 'same-origin',
          headers: {
            Accept: RECOVERY_FILE_MEDIA_TYPE,
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ workspace_secret: recoveryCode }),
        },
      )
      if (!response.ok) throw await errorFromResponse(response)
      const mediaType = (response.headers.get('Content-Type') || '').split(';')[0]
      if (mediaType !== RECOVERY_FILE_MEDIA_TYPE) {
        throw new Error('服务器返回的恢复文件类型不正确，已停止保存。')
      }
      const blob = await response.blob()
      if (!blob.size || blob.size > MAX_RECOVERY_FILE_BYTES) {
        throw new Error('服务器返回的恢复文件大小异常，已停止保存。')
      }
      saveBlob(blob, 'kmfa-workspace.kmfa-recovery')
      setMessage('`.kmfa-recovery` 下载已发起。它等同于完整控制权，请离线保存且不要分享。')
    })
  }

  const copyRecoveryCode = () => {
    if (!recoveryCode) return
    run(async () => {
      if (!window.navigator.clipboard?.writeText) {
        throw new Error('当前浏览器不允许安全复制；请手动选择并复制恢复码。')
      }
      await window.navigator.clipboard.writeText(recoveryCode)
      setMessage('恢复码已复制到系统剪贴板。请尽快保存到可信位置并清理不需要的副本。')
    })
  }

  const rotateRecoverySecret = () => {
    const confirmed = window.confirm(
      '轮换会立即撤销旧恢复码、旧 .kmfa-recovery 文件和全部旧短时会话，并为本页签发替代会话。确认继续？',
    )
    if (!confirmed) return
    run(async () => {
      const result = await jsonRequest(
        `/workspaces/${workspace.workspace_id}/recovery-secret/rotate`,
        {
          method: 'POST',
        },
      )
      setRecoveryCode(result.workspace_secret)
      setSession((current) => ({
        ...current,
        expiresAt: result.access_expires_at,
      }))
      setMessage('恢复密钥与会话已轮换：旧恢复材料和旧会话均已失效，本页已切换到新的受保护会话。')
    })
  }

  const saveWorkspace = (event) => {
    event.preventDefault()
    const form = new FormData(event.currentTarget)
    run(async () => {
      const result = await jsonRequest(`/workspaces/${workspace.workspace_id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
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
      const response = await fetchWithRiskChallenge(`${API_BASE}/workspaces/${workspace.workspace_id}/artifact`, {
        method: 'PUT',
        cache: 'no-store',
        credentials: 'same-origin',
        headers: {
          Accept: 'application/json',
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
      const response = await fetchWithRiskChallenge(
        `${API_BASE}/workspaces/${workspace.workspace_id}/artifact/download`,
        {
          method: 'POST',
          cache: 'no-store',
          credentials: 'same-origin',
        },
      )
      if (!response.ok) throw await errorFromResponse(response)
      const serverHash = response.headers.get('X-KMFA-Artifact-SHA256') || ''
      if (serverHash !== artifact.sha256) throw new Error('下载响应 hash 与项目记录不一致，已停止保存。')
      const blob = await response.blob()
      const browserHash = await sha256Hex(blob)
      if (browserHash !== serverHash) throw new Error('浏览器下载字节的 SHA-256 不一致，已停止保存。')
      saveBlob(blob, artifact.name)
      setMessage(`下载已发起；浏览器与服务器 SHA-256 一致：${browserHash}`)
    })
  }

  const revokePageSession = () => {
    run(async () => {
      const response = await fetchWithRiskChallenge(`${API_BASE}/sessions/current`, {
        method: 'DELETE',
        cache: 'no-store',
        credentials: 'same-origin',
      })
      if (!response.ok) throw await errorFromResponse(response)
      setSession(null)
      setRecoveryCode('')
      setRecoveryInput('')
      setRecoveryFile(null)
      setRecoveryFileKey((value) => value + 1)
      setProjectName('')
      setSelectedFile(null)
      setMode('recover')
      setMessage('短时会话已在服务器撤销并从浏览器清除；工作区和文件未删除。请使用恢复材料重新进入。')
    })
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
          这是 S03 骨架上的 S04 匿名安全切片，不是 GA：验证恢复、密钥轮换、项目进度、hash 下载，以及无需账号的分层限额、并发预算与一次性风险挑战。
          完整对象存储、备份演练、恶意文件扫描、多文件和明确删除仍将在后续阶段完成。
        </p>
      </div>

      {availability !== 'ready' ? (
        <SkeletonBoundary state={availability} retry={() => setStatusAttempt((value) => value + 1)} />
      ) : (
        <div className="walking-console" data-walking-ready="true">
          <div className="walking-recovery-warning" role="note" data-recovery-warning="visible">
            <strong>创建前先准备离线保存恢复材料</strong>
            <p>
              恢复码或 `.kmfa-recovery` 文件就是完整控制权。两者都丢失且本页会话结束后，平台无法通过账号、邮箱或客服找回；若材料泄露，请进入工作区后立即轮换。
            </p>
          </div>
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
                  <p>不要求账号、邮箱或 OAuth。可疑高频操作使用匿名计算挑战；恢复码只显示一次，平台不能通过邮箱找回。</p>
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
                  <p>或者导入由 KMFA 下载的严格格式恢复文件：</p>
                  <label htmlFor="walking-recovery-file">恢复文件（.kmfa-recovery）</label>
                  <input
                    key={recoveryFileKey}
                    id="walking-recovery-file"
                    type="file"
                    accept=".kmfa-recovery,application/vnd.kmfa.recovery+json"
                    data-recovery-file-input="true"
                    onChange={(event) => setRecoveryFile(event.target.files?.[0] || null)}
                  />
                  <button type="button" disabled={busy || !recoveryFile} onClick={importRecoveryFile}>
                    导入恢复文件
                  </button>
                  <p>恢复材料只在 POST 正文中处理，不进入 URL、localStorage、会话 Cookie 或第三方登录流程；Cookie 仅承载独立的短时会话凭据。</p>
                </form>
              )}
            </div>
          ) : (
            <div className="walking-workspace" data-workspace-ready="true">
              <div className="walking-workspace-head">
                <div>
                  <p className="walking-state-label">SERVER WORKSPACE</p>
                  <h3>{workspace.project_name}</h3>
                  <p>受保护短时会话到期：{session.expiresAt}</p>
                </div>
                <button type="button" className="walking-quiet" onClick={revokePageSession} disabled={busy}>
                  撤销并清除本页会话
                </button>
              </div>

              <div className="walking-recovery" data-recovery-management="ready">
                <strong>{recoveryCode ? '现在保存当前恢复材料' : '恢复文件已验证'}</strong>
                {recoveryCode ? (
                  <code data-recovery-code-value="true">{recoveryCode}</code>
                ) : (
                  <p>服务端没有回传恢复文件内的密钥。请保留已导入的文件；也可轮换并生成全新的恢复码与文件。</p>
                )}
                <p>
                  恢复材料等同于完整控制权；不要分享、不要放进 URL。轮换会撤销旧恢复材料和全部旧会话，并原子签发本页替代会话。
                </p>
                <div className="walking-recovery-actions">
                  <button type="button" onClick={copyRecoveryCode} disabled={busy || !recoveryCode}>
                    复制恢复码
                  </button>
                  <button
                    type="button"
                    data-recovery-file-download="true"
                    onClick={downloadRecoveryFile}
                    disabled={busy || !recoveryCode}
                  >
                    下载 .kmfa-recovery
                  </button>
                  <button
                    type="button"
                    data-recovery-rotate="true"
                    onClick={rotateRecoverySecret}
                    disabled={busy}
                  >
                    轮换并撤销旧密钥
                  </button>
                </div>
              </div>

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
        <span role="listitem">恢复码与文件服务端只存 hash</span>
        <span role="listitem">HttpOnly 短时会话可撤销</span>
        <span role="listitem">文件不进入静态公开目录</span>
        <span role="listitem">轮换撤销旧材料且不删状态</span>
        <span role="listitem">四层预算与一次性挑战，不强制登录</span>
      </div>
    </section>
  )
}

export default WalkingSkeleton
