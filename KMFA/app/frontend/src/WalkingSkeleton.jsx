import React, { useEffect, useMemo, useState } from 'react'

const API_BASE = '/public-api/walking-skeleton/v1'
const RECOVERY_FILE_MEDIA_TYPE = 'application/vnd.kmfa.recovery+json'
const MAX_RECOVERY_FILE_BYTES = 4096
const DOWNLOAD_RANGE_CHUNK_BYTES = 4 * 1024 * 1024
const MAX_BATCH_DOWNLOAD_ASSETS = 500

const ERROR_COPY = {
  walking_skeleton_disabled: '早期骨架当前处于安全回滚状态。已有服务器状态不会因此删除。',
  walking_skeleton_storage_unavailable: '服务器耐久存储暂不可用，未执行本次操作。',
  workspace_not_found: '工作区不存在、会话已过期，或当前会话无权访问。请使用恢复码重新恢复。',
  recovery_not_found: '恢复码或恢复文件无效、已截断或已被轮换撤销。平台无法通过邮箱代找回。',
  request_validation_failed: '请求格式或字段长度无效；服务器未回显提交内容。',
  invalid_recovery_file: '文件不是 KMFA 恢复文件；未授予任何访问。',
  recovery_file_too_large: '恢复文件超过 4 KiB 安全上限；未读取或授予访问。',
  invalid_project_name: '项目名不能为空，也不能包含控制字符。',
  invalid_filename: '文件名无效。请选择不含路径或控制字符的文件。',
  artifact_too_large: '文件超过服务器当前公开的单文件上限；超限字节未写入。',
  artifact_version_limit_reached: '该逻辑文件已达到不可变版本上限；既有版本与派生物未被覆盖。',
  artifact_upload_in_progress: '该工作区已有上传正在收敛；请等待完成后再提交下一版本。',
  artifact_integrity_failed: '下载完整性校验失败，服务器已阻止返回损坏字节。',
  artifact_unavailable: '文件当前不可读取，服务器没有返回替代或伪造内容。',
  artifact_download_not_found: '所选文件不属于当前工作区、已删除或不可下载。',
  single_file_download_disabled: '逐项下载 Flag 已回滚；既有文件未删除，当前版本原件仍可使用兼容下载。',
  range_batch_download_disabled: '续传与批量 ZIP Flag 已回滚；逐项下载和既有文件仍保持可用。',
  invalid_range_header: '续传区间格式无效；服务器未返回不确定字节。',
  range_not_satisfiable: '续传区间超出文件边界；请重新从服务器记录的大小开始。',
  duplicate_download_asset: '批量选择包含重复项目；服务器拒绝静默覆盖。',
  batch_asset_count_invalid: '批量下载必须选择 1–500 个不同项目。',
  batch_download_bytes_exceeded: '本次批量下载超过服务器公开的项目字节预算。',
  batch_archive_too_large: '批量归档超过当前安全 ZIP 边界；单文件下载仍可使用。',
  batch_archive_unavailable: '批量归档无法安全生成；服务器未返回不完整归档。',
  workspace_capacity_reached: '当前匿名灰度容量已满；公共浏览仍可用，已有工作区没有被删除。',
  artifact_capacity_reached: '当前文件存储预算不足；本次文件未写入，已有文件没有被删除。',
  invalid_idempotency_key: '上传重试标识无效；服务器未写入文件。',
  idempotency_key_conflict: '同一上传重试标识对应了不同文件或元数据；服务器拒绝混用。',
  artifact_upload_isolated: '上传进入可审计隔离态；原始对象未被删除，请勿把本次操作视为完成。',
  artifact_security_pending: '文件仍在隔离扫描中；扫描完成前不会返回原始字节，请稍后重新恢复或刷新工作区。',
  artifact_security_rejected: '文件命中安全拒绝规则并保持隔离，服务器不会提供下载、执行或预览。',
  file_security_unavailable: '文件安全扫描配置暂不可用；服务器未把未知结果标记为安全。',
  artifact_preview_disabled: '安全预览 Flag 已回滚；原件、版本、血缘和既有派生物仍保留。',
  artifact_preview_pending: '安全文本派生物尚未生成；请稍后刷新处理状态。',
  artifact_preview_unavailable: '当前版本不是可安全派生的纯文本，或派生对象暂不可用。',
  artifact_preview_integrity_failed: '预览派生物完整性校验失败，服务器已阻止返回。',
  processor_registry_conflict: '处理器登记与当前实现不一致，系统已停止生成新派生物。',
  processing_request_capacity_reached: '该版本已达到受控重处理次数上限；既有派生物仍可验证。',
  consistency_processing_paused: '新上传已按回滚预案暂停；既有项目、恢复材料和文件仍被保留。',
  consistency_mode_invalid: '一致性运行模式配置无效；服务器已停止接收新上传。',
  resumable_upload_disabled: '断点续传当前已安全回滚；可重新选择不超过标准上传上限的文件。',
  upload_session_not_found: '上传会话不存在、已取消，或不属于当前工作区。',
  upload_session_not_active: '上传会话已进入完成或隔离状态，不能继续写入分片。',
  upload_session_isolated: '上传完整性无法确认，会话已隔离且未发布为可下载文件。',
  upload_session_not_cancellable: '上传已进入最终写入阶段，不能再取消；请查询工作区确认结果。',
  upload_session_capacity_reached: '该工作区的历史上传会话已达到安全上限；既有项目和文件未被删除。',
  invalid_upload_checksum: '上传校验值格式无效；服务器未接受本次字节。',
  invalid_upload_offset: '上传偏移无效；请重新点击上传，让客户端从服务器偏移恢复。',
  invalid_upload_chunk_media_type: '分片媒体类型无效；服务器未接受本次字节。',
  invalid_upload_content_encoding: '分片必须发送原始 identity 字节；服务器拒绝压缩编码正文。',
  upload_chunk_size_invalid: '分片大小不符合服务器公开合同；服务器未接受本次分片。',
  upload_chunk_checksum_mismatch: '分片 SHA-256 不一致；该分片未进入耐久暂存。',
  upload_chunk_interrupted: '连接在分片完成前中断；不完整分片已丢弃，重新点击即可从已确认偏移继续。',
  upload_chunk_conflict: '该偏移已有不同字节；服务器拒绝覆盖，请重新选择原文件。',
  upload_offset_conflict: '客户端偏移已过期；请重新点击上传，从服务器记录的偏移恢复。',
  upload_chunk_state_invalid: '服务器检测到不连续分片并已停止完成操作，未发布文件。',
  upload_incomplete: '文件尚未上传完整；请重新点击上传，从已有偏移继续。',
  upload_checksum_mismatch: '完整文件 SHA-256 不一致；服务器未发布或返回受损文件。',
  resumable_storage_unavailable: '断点续传暂存不可用；已保存的项目和既有文件不受影响。',
  workspace_audit_capacity_reached: '该早期工作区已达到审计安全上限；本次变更未执行。',
  secret_in_url_rejected: '请求 URL 或来源页包含恢复材料，服务器已拒绝处理。请只通过受保护的表单正文提交。',
  cross_origin_session_request_rejected: '会话操作不是从 KMFA 同源页面发起，服务器已拒绝处理。',
  risk_capacity_limited: '匿名资源预算当前繁忙；公共浏览仍可使用，请按服务器提示稍后重试。',
  risk_challenge_required: '需要完成一次匿名安全校验后重试；不要求登录或提供个人资料。',
  risk_challenge_invalid: '匿名安全校验无效或已过期；未执行本次操作。',
  risk_challenge_replayed: '匿名安全校验已经使用，不能重放；未执行本次操作。',
  abuse_control_unavailable: '匿名资源保护暂不可用；受保护操作已安全关闭，公共浏览保持可用。',
  abuse_policy_configuration_invalid: '匿名资源策略配置无效；受保护操作已安全关闭。',
}

const SECURITY_STATE_COPY = {
  quarantined: '已隔离，等待扫描',
  scanning: '正在隔离扫描',
  clean: '有界检查通过；原件仍只作附件',
  attachment_only: '已分类为仅附件；不执行、不预览',
  rejected: '安全规则拒绝；保持隔离且禁止下载',
  timed_out: '扫描超时；未标记安全，仅允许附件下载',
  scanner_error: '扫描异常；未标记安全，仅允许附件下载',
  unscanned_attachment_only: '既有或回滚文件；未标记安全，仅允许附件下载',
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
  error.status = response.status
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
  if (value >= 1024 * 1024 * 1024) {
    return `${(value / (1024 * 1024 * 1024)).toFixed(1)} GiB`
  }
  if (value >= 1024 * 1024) {
    return `${(value / (1024 * 1024)).toFixed(value < 100 * 1024 * 1024 ? 1 : 0)} MiB`
  }
  return `${(value / 1024).toFixed(value < 1024 * 100 ? 1 : 0)} KiB`
}

async function sha256Hex(blob) {
  const digest = await window.crypto.subtle.digest('SHA-256', await blob.arrayBuffer())
  return Array.from(new Uint8Array(digest), (byte) => byte.toString(16).padStart(2, '0')).join('')
}

function downloadSelectorKey(item) {
  return `${item.kind}:${item.id}`
}

function validateExactDownloadResponse(response, expected) {
  const serverHash = response.headers.get('X-KMFA-Artifact-SHA256') || ''
  if (serverHash !== expected.sha256) {
    throw new Error('下载响应 hash 与项目记录不一致，已停止保存。')
  }
  const disposition = response.headers.get('Content-Disposition') || ''
  if (!disposition.toLowerCase().startsWith('attachment;')) {
    throw new Error('下载响应不是附件模式，已停止保存。')
  }
  const responseKind = response.headers.get('X-KMFA-Artifact-Kind') || ''
  const responseId = response.headers.get('X-KMFA-Artifact-ID') || ''
  const responseSize = response.headers.get('X-KMFA-Artifact-Size') || ''
  const recordedMediaType = response.headers.get('X-KMFA-Artifact-Media-Type') || ''
  const sourceVersion = response.headers.get('X-KMFA-Source-Artifact-Version') || ''
  const responseMediaType = (
    response.headers.get('Content-Type') || ''
  ).split(';', 1)[0].toLowerCase()
  const expectedResponseMediaType = expected.media_type
    .split(';', 1)[0]
    .trim()
    .toLowerCase()
  if (
    responseKind !== expected.kind
    || responseId !== expected.id
    || responseSize !== String(expected.size_bytes)
    || recordedMediaType !== expected.media_type
    || sourceVersion !== expected.source?.artifact_version_id
    || responseMediaType !== expectedResponseMediaType
  ) {
    throw new Error('下载响应元数据与所选文件不一致，已停止保存。')
  }
  if (expected.kind === 'derivative') {
    const processor = expected.source?.processor
    const expectedProcessor = processor
      ? `${processor.name}/${processor.version}`
      : ''
    if (response.headers.get('X-KMFA-Processor') !== expectedProcessor) {
      throw new Error('下载派生物的处理器来源不一致，已停止保存。')
    }
  } else if (
    expected.source?.operation_id
    && response.headers.get('X-KMFA-Source-Operation')
      !== expected.source.operation_id
  ) {
    throw new Error('下载原件的上传来源不一致，已停止保存。')
  }
  return {
    serverHash,
    etag: response.headers.get('ETag') || '',
  }
}

async function uploadIdempotencyKeyFor(
  workspaceId,
  file,
  bodyHash = '',
  nextVersion = 1,
) {
  const resolvedBodyHash = bodyHash || await sha256Hex(file)
  const identity = JSON.stringify([
    workspaceId,
    file.name,
    file.type || 'application/octet-stream',
    file.size,
    resolvedBodyHash,
    nextVersion,
  ])
  const digest = await window.crypto.subtle.digest(
    'SHA-256',
    new TextEncoder().encode(identity),
  )
  const hex = Array.from(
    new Uint8Array(digest),
    (byte) => byte.toString(16).padStart(2, '0'),
  ).join('')
  return `upload_${hex}`
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
  const [limits, setLimits] = useState({
    maxBytes: 8 * 1024 * 1024,
    maxArtifacts: 1,
    maxVersions: 32,
    maxTotalBytes: 512 * 1024 * 1024,
    maxChunkBytes: 4 * 1024 * 1024,
    maxSessions: 16,
  })
  const [resumableUpload, setResumableUpload] = useState(false)
  const [fileSecurity, setFileSecurity] = useState(false)
  const [artifactDerivation, setArtifactDerivation] = useState(false)
  const [singleFileDownload, setSingleFileDownload] = useState(false)
  const [rangeBatchDownload, setRangeBatchDownload] = useState(false)
  const [selectedDownloadKeys, setSelectedDownloadKeys] = useState([])
  const [batchAbortController, setBatchAbortController] = useState(null)
  const [previewText, setPreviewText] = useState('')
  const [uploadProgress, setUploadProgress] = useState(null)
  const [mode, setMode] = useState('create')
  const [projectName, setProjectName] = useState('')
  const [recoveryInput, setRecoveryInput] = useState('')
  const [recoveryCode, setRecoveryCode] = useState('')
  const [recoveryFile, setRecoveryFile] = useState(null)
  const [recoveryFileKey, setRecoveryFileKey] = useState(0)
  const [session, setSession] = useState(null)
  const [selectedFile, setSelectedFile] = useState(null)
  const [uploadIdempotencyKey, setUploadIdempotencyKey] = useState('')
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
        const resumableEnabled = status.resumable_upload?.enabled === true
        setLimits({
          maxBytes: resumableEnabled
            ? status.resumable_upload?.max_file_bytes || 64 * 1024 * 1024
            : status.limits?.max_bytes || 8 * 1024 * 1024,
          maxArtifacts: status.limits?.max_artifacts || 1,
          maxVersions: status.limits?.max_versions_per_artifact || 32,
          maxTotalBytes: status.limits?.max_total_artifact_bytes || 512 * 1024 * 1024,
          maxChunkBytes: status.resumable_upload?.max_chunk_bytes || 4 * 1024 * 1024,
          maxSessions: status.resumable_upload?.max_sessions_per_workspace || 16,
        })
        setResumableUpload(resumableEnabled)
        setFileSecurity(status.file_security?.enabled === true)
        setArtifactDerivation(status.artifact_derivation?.enabled === true)
        setSingleFileDownload(status.single_file_download?.enabled === true)
        setRangeBatchDownload(status.range_batch_download?.enabled === true)
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
  const downloadables = (
    singleFileDownload && Array.isArray(artifact?.downloadables)
      ? artifact.downloadables
      : []
  )
  const selectedBatchItems = downloadables.filter(
    (item) => selectedDownloadKeys.includes(downloadSelectorKey(item))
      && item.download_allowed !== false,
  )
  const versionLimitReached = (
    Number(artifact?.version_count || 0) >= limits.maxVersions
  )
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
      const fullHash = resumableUpload ? await sha256Hex(selectedFile) : ''
      const retryKey = uploadIdempotencyKey
        || await uploadIdempotencyKeyFor(
          workspace.workspace_id,
          selectedFile,
          fullHash,
          Number(artifact?.version_number || 0) + 1,
        )
      if (!uploadIdempotencyKey) setUploadIdempotencyKey(retryKey)
      let result
      if (resumableUpload) {
        const created = await jsonRequest(
          `/workspaces/${workspace.workspace_id}/upload-sessions`,
          {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              'Idempotency-Key': retryKey,
            },
            body: JSON.stringify({
              original_name: selectedFile.name,
              reported_media_type: selectedFile.type || 'application/octet-stream',
              size_bytes: selectedFile.size,
              sha256: fullHash,
            }),
          },
        )
        const uploadSession = created?.upload_session
        const uploadSessionId = String(uploadSession?.upload_session_id || '')
        let offset = Number(uploadSession?.offset_bytes)
        const sessionChunkBytes = Number(uploadSession?.max_chunk_bytes)
        if (
          !/^operation_[A-Za-z0-9_-]{24}$/.test(uploadSessionId)
          || uploadSession?.protocol !== 'kmfa-offset-v1'
          || Number(uploadSession?.size_bytes) !== selectedFile.size
          || uploadSession?.sha256 !== fullHash
          || !Number.isSafeInteger(offset)
          || offset < 0
          || offset > selectedFile.size
          || !Number.isSafeInteger(sessionChunkBytes)
          || sessionChunkBytes < 1
          || sessionChunkBytes > limits.maxChunkBytes
        ) {
          throw new Error('服务器返回的断点续传合同无效，已停止发送文件字节。')
        }
        setUploadProgress({ offset, total: selectedFile.size })
        const sessionPath = (
          `/workspaces/${workspace.workspace_id}/upload-sessions/${uploadSessionId}`
        )
        while (offset < selectedFile.size) {
          const nextExpected = Math.min(
            selectedFile.size,
            offset + sessionChunkBytes,
          )
          const chunk = selectedFile.slice(offset, nextExpected)
          const chunkHash = await sha256Hex(chunk)
          const response = await fetchWithRiskChallenge(
            `${API_BASE}${sessionPath}`,
            {
              method: 'PATCH',
              cache: 'no-store',
              credentials: 'same-origin',
              headers: {
                Accept: 'application/json',
                'Content-Type': 'application/offset+octet-stream',
                'Upload-Offset': String(offset),
                'X-KMFA-Chunk-SHA256': chunkHash,
              },
              body: chunk,
            },
          )
          if (!response.ok) throw await errorFromResponse(response)
          const nextOffset = Number(response.headers.get('Upload-Offset'))
          if (nextOffset !== nextExpected) {
            throw new Error('服务器返回的上传偏移不连续；已停止继续发送文件字节。')
          }
          offset = nextOffset
          setUploadProgress({ offset, total: selectedFile.size })
        }
        result = await jsonRequest(`${sessionPath}/complete`, {
          method: 'POST',
        })
      } else {
        const response = await fetchWithRiskChallenge(
          `${API_BASE}/workspaces/${workspace.workspace_id}/artifact`,
          {
            method: 'PUT',
            cache: 'no-store',
            credentials: 'same-origin',
            headers: {
              Accept: 'application/json',
              'Content-Type': selectedFile.type || 'application/octet-stream',
              'X-KMFA-Filename': encodeURIComponent(selectedFile.name),
              'Idempotency-Key': retryKey,
            },
            body: selectedFile,
          },
        )
        if (!response.ok) throw await errorFromResponse(response)
        result = await response.json()
      }
      setSession((current) => ({ ...current, workspace: result }))
      setSelectedFile(null)
      setUploadIdempotencyKey('')
      setUploadProgress(null)
      setPreviewText('')
      form.reset()
      const securityState = result.artifact?.security?.state || 'unscanned_attachment_only'
      const securityCopy = SECURITY_STATE_COPY[securityState] || '安全状态待确认'
      setMessage(`不可变版本 v${result.artifact.version_number} 已写入私有耐久存储。${securityCopy}。SHA-256：${result.artifact.sha256}`)
    })
  }

  const refreshWorkspace = () => {
    run(async () => {
      const result = await jsonRequest(
        `/workspaces/${workspace.workspace_id}`,
      )
      setSession((current) => ({ ...current, workspace: result }))
      setPreviewText('')
      setMessage('已从服务器刷新版本、扫描与派生状态。')
    })
  }

  const previewArtifact = () => {
    run(async () => {
      const response = await fetchWithRiskChallenge(
        `${API_BASE}/workspaces/${workspace.workspace_id}/artifact/preview`,
        {
          method: 'GET',
          cache: 'no-store',
          credentials: 'same-origin',
          headers: { Accept: 'text/plain' },
        },
      )
      if (!response.ok) throw await errorFromResponse(response)
      const serverHash = response.headers.get('X-KMFA-Derivative-SHA256') || ''
      if (!artifact.preview || serverHash !== artifact.preview.sha256) {
        throw new Error('预览响应 hash 与当前派生记录不一致，已停止显示。')
      }
      const blob = await response.blob()
      const browserHash = await sha256Hex(blob)
      if (browserHash !== serverHash) {
        throw new Error('浏览器收到的预览字节校验失败，已停止显示。')
      }
      setPreviewText(await blob.text())
      setMessage(`纯文本预览已验证；处理器 ${artifact.preview.processor.name}/${artifact.preview.processor.version}，SHA-256：${browserHash}`)
    })
  }

  const reprocessArtifact = () => {
    run(async () => {
      const key = `reprocess_${window.crypto.randomUUID().replaceAll('-', '')}`
      const result = await jsonRequest(
        `/workspaces/${workspace.workspace_id}/artifact/reprocess`,
        {
          method: 'POST',
          headers: { 'Idempotency-Key': key },
        },
      )
      setMessage(`已登记不可变重处理请求 ${result.processing_run_id}；原件未改写。稍后刷新处理状态。`)
    })
  }

  const downloadArtifact = (target = null) => {
    run(async () => {
      const exactTarget = (
        singleFileDownload
        && target
        && typeof target.id === 'string'
      )
      const expected = exactTarget
        ? target
        : {
            id: artifact.artifact_version_id,
            kind: 'original',
            name: artifact.name,
            media_type: artifact.media_type || 'application/octet-stream',
            size_bytes: artifact.size_bytes,
            sha256: artifact.sha256,
            source: artifact.source || {
              artifact_version_id: artifact.artifact_version_id,
            },
          }
      const exactUrl = `${API_BASE}/workspaces/${workspace.workspace_id}/artifact/downloads`
      const exactBody = JSON.stringify({
        kind: expected.kind,
        asset_id: expected.id,
      })
      let blob
      let serverHash = ''
      let usedRangeResume = false

      if (
        exactTarget
        && rangeBatchDownload
        && Number(expected.size_bytes) > 0
      ) {
        const chunks = []
        let offset = 0
        let stableEtag = ''
        while (offset < expected.size_bytes) {
          const end = Math.min(
            expected.size_bytes - 1,
            offset + DOWNLOAD_RANGE_CHUNK_BYTES - 1,
          )
          let response = null
          let lastNetworkError = null
          for (let attempt = 0; attempt < 2; attempt += 1) {
            try {
              response = await fetchWithRiskChallenge(exactUrl, {
                method: 'POST',
                cache: 'no-store',
                credentials: 'same-origin',
                headers: {
                  Accept: 'application/octet-stream',
                  'Content-Type': 'application/json',
                  Range: `bytes=${offset}-${end}`,
                  ...(stableEtag ? { 'If-Range': stableEtag } : {}),
                },
                body: exactBody,
              })
              lastNetworkError = null
            } catch (caught) {
              lastNetworkError = caught
              response = null
            }
            if (response !== null) break
          }
          if (response === null) throw lastNetworkError
          if (!response.ok) throw await errorFromResponse(response)
          if (response.status !== 206) {
            throw new Error('续传响应没有返回明确的 206 区间，已停止拼接。')
          }
          const verified = validateExactDownloadResponse(response, expected)
          serverHash = verified.serverHash
          if (!stableEtag) stableEtag = verified.etag
          if (!stableEtag || verified.etag !== stableEtag) {
            throw new Error('续传期间文件验证标识发生变化，已停止拼接。')
          }
          const expectedRange = `bytes ${offset}-${end}/${expected.size_bytes}`
          if (
            response.headers.get('Content-Range') !== expectedRange
            || response.headers.get('Accept-Ranges') !== 'bytes'
          ) {
            throw new Error('续传响应区间与请求不一致，已停止拼接。')
          }
          const chunk = await response.blob()
          if (chunk.size !== end - offset + 1) {
            throw new Error('续传分片字节数不一致，已停止拼接。')
          }
          chunks.push(chunk)
          offset = end + 1
        }
        blob = new Blob(chunks, { type: expected.media_type })
        usedRangeResume = true
      } else {
        const response = await fetchWithRiskChallenge(
          exactTarget
            ? exactUrl
            : `${API_BASE}/workspaces/${workspace.workspace_id}/artifact/download`,
          {
            method: 'POST',
            cache: 'no-store',
            credentials: 'same-origin',
            headers: exactTarget
              ? {
                  Accept: 'application/octet-stream',
                  'Content-Type': 'application/json',
                }
              : undefined,
            body: exactTarget ? exactBody : undefined,
          },
        )
        if (!response.ok) throw await errorFromResponse(response)
        if (exactTarget) {
          serverHash = validateExactDownloadResponse(
            response,
            expected,
          ).serverHash
        } else {
          serverHash = response.headers.get('X-KMFA-Artifact-SHA256') || ''
          if (serverHash !== expected.sha256) {
            throw new Error('下载响应 hash 与项目记录不一致，已停止保存。')
          }
          const disposition = response.headers.get('Content-Disposition') || ''
          if (!disposition.toLowerCase().startsWith('attachment;')) {
            throw new Error('下载响应不是附件模式，已停止保存。')
          }
        }
        blob = await response.blob()
      }
      if (blob.size !== expected.size_bytes) {
        throw new Error('浏览器收到的下载字节数不一致，已停止保存。')
      }
      const browserHash = await sha256Hex(blob)
      if (browserHash !== serverHash) throw new Error('浏览器下载字节的 SHA-256 不一致，已停止保存。')
      saveBlob(blob, expected.name)
      setMessage(
        `已校验并下载 ${expected.name}；${usedRangeResume ? '固定分片续传、' : ''}类型、大小、来源与 SHA-256 均一致：${browserHash}`,
      )
    })
  }

  const toggleDownloadSelection = (item) => {
    const key = downloadSelectorKey(item)
    setSelectedDownloadKeys((current) => {
      if (current.includes(key)) {
        return current.filter((candidate) => candidate !== key)
      }
      if (current.length >= MAX_BATCH_DOWNLOAD_ASSETS) return current
      return [...current, key]
    })
  }

  const downloadSelectedBatch = () => {
    run(async () => {
      if (
        selectedBatchItems.length < 1
        || selectedBatchItems.length > MAX_BATCH_DOWNLOAD_ASSETS
      ) {
        throw new Error(ERROR_COPY.batch_asset_count_invalid)
      }
      const expectedSourceBytes = selectedBatchItems.reduce(
        (total, item) => total + Number(item.size_bytes),
        0,
      )
      const url = `${API_BASE}/workspaces/${workspace.workspace_id}/artifact/downloads/batch`
      const body = JSON.stringify({
        assets: selectedBatchItems.map((item) => ({
          kind: item.kind,
          asset_id: item.id,
        })),
      })
      const controller = new AbortController()
      setBatchAbortController(controller)
      let archive = null
      let manifestHash = ''
      let lastError = null
      try {
        for (let attempt = 0; attempt < 2; attempt += 1) {
          try {
            const response = await fetchWithRiskChallenge(url, {
              method: 'POST',
              cache: 'no-store',
              credentials: 'same-origin',
              signal: controller.signal,
              headers: {
                Accept: 'application/zip',
                'Content-Type': 'application/json',
              },
              body,
            })
            if (!response.ok) throw await errorFromResponse(response)
            manifestHash = (
              response.headers.get('X-KMFA-ZIP-Manifest-SHA256') || ''
            )
            const disposition = response.headers.get('Content-Disposition') || ''
            const contentLength = Number(response.headers.get('Content-Length'))
            if (
              response.headers.get('X-KMFA-Batch-File-Count')
                !== String(selectedBatchItems.length)
              || response.headers.get('X-KMFA-Batch-Source-Bytes')
                !== String(expectedSourceBytes)
              || response.headers.get('X-KMFA-ZIP-Format')
                !== 'zip-stored-stream-v1'
              || response.headers.get('X-KMFA-ZIP-Manifest-Path')
                !== 'manifest.json'
              || !/^[0-9a-f]{64}$/.test(manifestHash)
              || !disposition.toLowerCase().startsWith('attachment;')
              || !Number.isSafeInteger(contentLength)
              || contentLength <= 0
            ) {
              throw new Error('批量归档响应合同不完整，已停止保存。')
            }
            archive = await response.blob()
            if (
              archive.size !== contentLength
              || (archive.type && archive.type !== 'application/zip')
            ) {
              throw new Error('批量归档字节未完整送达，已停止保存。')
            }
            lastError = null
            break
          } catch (caught) {
            if (controller.signal.aborted) {
              throw new Error('已取消本次批量下载；已保存文件和项目未改变，可重新发起。')
            }
            if (
              Number.isInteger(caught?.status)
              && caught.status < 500
            ) {
              throw caught
            }
            lastError = caught
            archive = null
          }
        }
      } finally {
        setBatchAbortController(null)
      }
      if (archive === null) throw lastError
      saveBlob(archive, 'kmfa-downloads.zip')
      setMessage(
        `已下载 ${selectedBatchItems.length} 项流式 ZIP；manifest SHA-256：${manifestHash}，解压后可按其中逐项 SHA-256 验证。`,
      )
    })
  }

  const cancelBatchDownload = () => {
    batchAbortController?.abort()
  }

  const revokePageSession = () => {
    run(async () => {
      batchAbortController?.abort()
      const response = await fetchWithRiskChallenge(`${API_BASE}/sessions/current`, {
        method: 'DELETE',
        cache: 'no-store',
        credentials: 'same-origin',
      })
      if (!response.ok) throw await errorFromResponse(response)
      setSession(null)
      setPreviewText('')
      setRecoveryCode('')
      setRecoveryInput('')
      setRecoveryFile(null)
      setRecoveryFileKey((value) => value + 1)
      setProjectName('')
      setSelectedFile(null)
      setSelectedDownloadKeys([])
      setUploadProgress(null)
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
          这是 S03 骨架上的 S06 上传链与 S07/P7.2 可续传下载切片，不是 GA：文件通过耐久意图与私有对象路径保存，先隔离，再由无数据库/对象凭据的私网扫描器分类。
          未知、高风险、超时或异常结果不会冒充安全；拒绝项不下载，原件永不执行。逐项下载按固定 Range 分片核对来源与 SHA-256；批量 ZIP 逐项流出、带 manifest/hash 且不在服务器内存组装整包。导出 Job 与公开快照仍由后续 phase 接管。
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
                    onChange={(event) => {
                      const file = event.target.files?.[0] || null
                      setSelectedFile(file)
                      setUploadIdempotencyKey('')
                      setUploadProgress(null)
                    }}
                    disabled={versionLimitReached}
                  />
                  <p data-upload-quota="visible">
                    单版本上限 {formatBytes(limits.maxBytes)}；当前工作区保留 {limits.maxArtifacts} 个逻辑文件、最多 {limits.maxVersions} 个不可变版本，阶段总文件预算 {formatBytes(limits.maxTotalBytes)}。
                    {resumableUpload
                      ? ` 每片最多 ${formatBytes(limits.maxChunkBytes)}，每个工作区最多保留 ${limits.maxSessions} 个历史上传会话；连接中断后重新选择同一文件即可从服务器偏移继续。`
                      : ' 断点续传已回滚，当前使用标准上传路径。'}
                    {fileSecurity
                      ? ' 文件先隔离再扫描；未知/高风险格式只作附件，拒绝项不下载。'
                      : ' 隔离扫描 Flag 当前回滚；既有或未决文件只作附件。'}
                    {artifactDerivation
                      ? ' 仅 clean 的 UTF-8 文本由独立 worker 生成有界纯文本派生物；任何内容均不执行。'
                      : ' 安全预览 Flag 当前回滚；所有状态均不执行、不预览。'}
                  </p>
                  {uploadProgress && (
                    <div
                      className="walking-upload-progress"
                      data-upload-progress="visible"
                      data-upload-offset={uploadProgress.offset}
                      data-upload-total={uploadProgress.total}
                    >
                      <progress
                        max={Math.max(uploadProgress.total, 1)}
                        value={uploadProgress.offset}
                      />
                      <span>
                        已确认 {formatBytes(uploadProgress.offset)} / {formatBytes(uploadProgress.total)}
                      </span>
                    </div>
                  )}
                  <button type="submit" disabled={busy || versionLimitReached}>
                    {versionLimitReached
                      ? '已达到版本上限'
                      : uploadProgress
                        ? busy
                          ? '正在断点续传'
                          : '继续断点上传'
                        : artifact
                          ? '上传为下一不可变版本'
                          : '上传到服务器'}
                  </button>
                </form>

                <div
                  className="walking-card walking-artifact"
                  data-walking-artifact={artifact ? 'ready' : 'empty'}
                  data-security-state={artifact?.security?.state || 'none'}
                >
                  <p className="walking-card-code">03 / VERIFY + DOWNLOAD</p>
                  {artifact ? (
                    <>
                      <h4>{artifact.name}</h4>
                      <dl>
                        <div><dt>版本</dt><dd>v{artifact.version_number} / {artifact.version_count}</dd></div>
                        <div><dt>类型</dt><dd>{artifact.media_type || 'application/octet-stream'}</dd></div>
                        <div><dt>字节</dt><dd>{artifact.size_bytes}</dd></div>
                        <div><dt>模式</dt><dd>attachment-only</dd></div>
                        <div>
                          <dt>安全状态</dt>
                          <dd>
                            {SECURITY_STATE_COPY[artifact.security?.state]
                              || '安全状态待确认'}
                          </dd>
                        </div>
                        <div><dt>SHA-256</dt><dd><code>{artifact.sha256}</code></dd></div>
                      </dl>
                      <div className="walking-artifact-actions">
                        {downloadables.length === 0 && (
                          <button
                            type="button"
                            data-walking-download="true"
                            onClick={() => downloadArtifact()}
                            disabled={busy || artifact.download_allowed === false}
                          >
                            {artifact.download_allowed === false
                              ? '当前安全状态禁止下载'
                              : '校验并下载附件'}
                          </button>
                        )}
                        <button
                          type="button"
                          data-walking-refresh="true"
                          onClick={refreshWorkspace}
                          disabled={busy}
                        >
                          刷新处理状态
                        </button>
                        {artifact.preview_allowed && (
                          <button
                            type="button"
                            data-walking-preview="true"
                            onClick={previewArtifact}
                            disabled={busy}
                          >
                            校验并查看纯文本预览
                          </button>
                        )}
                        {artifact.security?.processing_allowed && (
                          <button
                            type="button"
                            data-walking-reprocess="true"
                            onClick={reprocessArtifact}
                            disabled={busy}
                          >
                            生成新的不可变派生物
                          </button>
                        )}
                      </div>
                      {downloadables.length > 0 && (
                        <section
                          className="walking-download-list"
                          aria-label="可续传单文件与批量 ZIP 下载"
                          data-walking-download-list="ready"
                        >
                          <h5>精确版本与派生物</h5>
                          <p>每项固定为附件；下载前后核对服务器记录与浏览器收到的字节。批量项进入独立目录，重名不会覆盖。</p>
                          {rangeBatchDownload && (
                            <div
                              className="walking-batch-actions"
                              data-walking-batch-selection={selectedBatchItems.length}
                            >
                              <span>
                                已选择 {selectedBatchItems.length} / {MAX_BATCH_DOWNLOAD_ASSETS} 项
                              </span>
                              <button
                                type="button"
                                data-walking-download-batch="true"
                                onClick={downloadSelectedBatch}
                                disabled={busy || selectedBatchItems.length === 0}
                              >
                                下载带 manifest/hash 的流式 ZIP
                              </button>
                              {batchAbortController && (
                                <button
                                  type="button"
                                  className="walking-batch-cancel"
                                  data-walking-download-batch-cancel="true"
                                  onClick={cancelBatchDownload}
                                >
                                  取消本次批量下载
                                </button>
                              )}
                            </div>
                          )}
                          {downloadables.map((item) => (
                            <article
                              key={`${item.kind}:${item.id}`}
                              data-walking-download-item={item.kind}
                              data-download-asset-id={item.id}
                            >
                              <strong>{item.name}</strong>
                              <span>
                                {item.kind === 'original'
                                  ? `上传原件 · v${item.version_number}`
                                  : `派生物 · 源 v${item.version_number} · ${item.source.processor.name}/${item.source.processor.version}`}
                              </span>
                              <span>{item.media_type} · {formatBytes(item.size_bytes)}</span>
                              <code>{item.sha256}</code>
                              {rangeBatchDownload && (
                                <label className="walking-download-choice">
                                  <input
                                    type="checkbox"
                                    data-walking-download-select={item.id}
                                    checked={selectedDownloadKeys.includes(downloadSelectorKey(item))}
                                    onChange={() => toggleDownloadSelection(item)}
                                    disabled={
                                      busy
                                      || item.download_allowed === false
                                      || (
                                        selectedBatchItems.length >= MAX_BATCH_DOWNLOAD_ASSETS
                                        && !selectedDownloadKeys.includes(downloadSelectorKey(item))
                                      )
                                    }
                                  />
                                  <span>加入批量 ZIP</span>
                                </label>
                              )}
                              <button
                                type="button"
                                data-walking-download="exact"
                                onClick={() => downloadArtifact(item)}
                                disabled={busy || item.download_allowed === false}
                              >
                                {item.download_allowed === false
                                  ? '当前安全状态禁止下载'
                                  : '校验来源并下载附件'}
                              </button>
                            </article>
                          ))}
                        </section>
                      )}
                      {previewText && (
                        <pre
                          className="walking-safe-preview"
                          data-walking-safe-preview="true"
                        >
                          {previewText}
                        </pre>
                      )}
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
        <span role="listitem">精确版本、来源与 SHA-256 可核验</span>
        <span role="listitem">强制附件；Range/ZIP/导出尚未启用</span>
        <span role="listitem">文件不进入静态公开目录</span>
        <span role="listitem">固定分片、服务器偏移与端到端 SHA-256</span>
        <span role="listitem">轮换撤销旧材料且不删状态</span>
        <span role="listitem">四层预算与一次性挑战，不强制登录</span>
      </div>
    </section>
  )
}

export default WalkingSkeleton
