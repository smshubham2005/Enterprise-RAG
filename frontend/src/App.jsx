import { useEffect, useRef, useState } from 'react'
import './App.css'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ||
  `${window.location.protocol}//${window.location.hostname}:8000`

const EXAMPLE_QUESTIONS = [
  'Summarize the uploaded document',
  'What are the key policies mentioned?',
  'List the most important obligations',
]

function formatBytes(sizeBytes) {
  if (!sizeBytes) return 'Size unknown'

  const units = ['B', 'KB', 'MB', 'GB']
  const unitIndex = Math.min(Math.floor(Math.log(sizeBytes) / Math.log(1024)), units.length - 1)
  const value = sizeBytes / 1024 ** unitIndex

  return `${value.toFixed(value >= 10 || unitIndex === 0 ? 0 : 1)} ${units[unitIndex]}`
}

function isPdfFile(file) {
  if (!file) return false

  const fileName = file.name?.toLowerCase() || ''
  const fileType = file.type?.toLowerCase() || ''

  return fileName.endsWith('.pdf') || fileType === 'application/pdf' || fileType === 'application/x-pdf'
}

async function readJsonSafely(response) {
  const text = await response.text()
  if (!text) return null

  try {
    return JSON.parse(text)
  } catch {
    return null
  }
}

const Icon = {
  Mark: (p) => (
    <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="1.6" {...p}>
      <path d="M6 3h9l3 3v15H6z" strokeLinejoin="round" />
      <path d="M15 3v3h3" strokeLinejoin="round" />
      <path d="M9 12h6M9 15.5h6M9 8.5h3" strokeLinecap="round" />
    </svg>
  ),
  Upload: (p) => (
    <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="1.8" {...p}>
      <path d="M12 16V4M12 4 7 9M12 4l5 5" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M4.5 15v3.5A1.5 1.5 0 0 0 6 20h12a1.5 1.5 0 0 0 1.5-1.5V15" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  ),
  Refresh: (p) => (
    <svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" strokeWidth="1.8" {...p}>
      <path d="M4 12a8 8 0 0 1 13.66-5.66L20 8M20 12a8 8 0 0 1-13.66 5.66L4 16" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M20 4v4h-4M4 20v-4h4" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  ),
  Send: (p) => (
    <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="1.8" {...p}>
      <path d="M4 12h15M12 5l7 7-7 7" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  ),
  Close: (p) => (
    <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="1.8" {...p}>
      <path d="M6 6l12 12M18 6 6 18" strokeLinecap="round" />
    </svg>
  ),
  Logout: (p) => (
    <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" strokeWidth="1.8" {...p}>
      <path d="M9 21H5a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1h4" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M16 17l5-5-5-5M21 12H9" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  ),
  Trash: (p) => (
    <svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" strokeWidth="1.8" {...p}>
      <path d="M4 7h16M9 7V5a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2M18 7l-.8 12.2a1.5 1.5 0 0 1-1.5 1.4H8.3a1.5 1.5 0 0 1-1.5-1.4L6 7" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M10 11v6M14 11v6" strokeLinecap="round" />
    </svg>
  ),
  ArrowDown: (p) => (
    <svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" strokeWidth="1.8" {...p}>
      <path d="M12 5v14M7 14l5 5 5-5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  ),
}

function App() {
  const [token, setToken] = useState(localStorage.getItem('rag_token') || '')
  const [username, setUsername] = useState(localStorage.getItem('rag_username') || '')
  const [loginUser, setLoginUser] = useState('')
  const [loginPass, setLoginPass] = useState('')
  const [loginError, setLoginError] = useState('')
  const [query, setQuery] = useState('')
  const [topK, setTopK] = useState(4)
  const [messages, setMessages] = useState([])
  const [activeSources, setActiveSources] = useState(null)
  const [error, setError] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [loadingMessage, setLoadingMessage] = useState('Searching documents...')
  const [documents, setDocuments] = useState([])
  const [documentError, setDocumentError] = useState('')
  const [isDocumentsLoading, setIsDocumentsLoading] = useState(true)
  const [selectedFile, setSelectedFile] = useState(null)
  const [uploadMessage, setUploadMessage] = useState('')
  const [uploadProgress, setUploadProgress] = useState(0)
  const [uploadStatus, setUploadStatus] = useState('idle')
  const [isUploading, setIsUploading] = useState(false)
  const [deletingDocument, setDeletingDocument] = useState('')
  const [isAtBottom, setIsAtBottom] = useState(true)

  const chatEndRef = useRef(null)
  const chatMessagesRef = useRef(null)
  const textareaRef = useRef(null)
  const fileInputRef = useRef(null)

  const canSubmit = query.trim().length > 0 && !isLoading
  const canUpload = !!selectedFile && !isUploading
  const totalChunks = documents.reduce((total, document) => total + document.chunk_count, 0)
  const indexedDocumentCount = documents.filter((document) => document.indexed).length

  useEffect(() => {
    if (token) {
      refreshDocuments()
      requestAnimationFrame(() => textareaRef.current?.focus())
    }
  }, [token])

  useEffect(() => {
    if (isAtBottom) {
      chatEndRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' })
    }
  }, [messages, isLoading, activeSources, isAtBottom])

  // Auto-expand query textarea height dynamically on query text change
  useEffect(() => {
    const textarea = textareaRef.current
    if (textarea) {
      textarea.style.height = 'auto'
      textarea.style.height = `${Math.min(textarea.scrollHeight, 200)}px`
    }
  }, [query])


  function handleChatScroll() {
    const container = chatMessagesRef.current
    if (!container) return
    const distanceFromBottom = container.scrollHeight - container.scrollTop - container.clientHeight
    setIsAtBottom(distanceFromBottom < 80)
  }

  function jumpToLatest() {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' })
    setIsAtBottom(true)
    textareaRef.current?.focus()
  }

  async function handleLogin(event) {
    event.preventDefault()
    setLoginError('')
    try {
      const response = await fetch(`${API_BASE_URL}/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username: loginUser, password: loginPass }),
      })
      const payload = await readJsonSafely(response)
      if (!response.ok) throw new Error(payload?.detail || 'Login failed')
      localStorage.setItem('rag_token', payload.access_token)
      localStorage.setItem('rag_username', payload.username)
      setToken(payload.access_token)
      setUsername(payload.username)
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Unable to sign in right now.'
      setLoginError(message === 'Failed to fetch' ? 'The sign-in service is unavailable right now. Please try again.' : message)
    }
  }

  function handleLogout() {
    localStorage.removeItem('rag_token')
    localStorage.removeItem('rag_username')
    setToken('')
    setUsername('')
    setMessages([])
    setDocuments([])
    setActiveSources(null)
  }

  async function refreshDocuments() {
    setIsDocumentsLoading(true)
    setDocumentError('')
    try {
      const response = await fetch(`${API_BASE_URL}/documents`, {
        headers: { Authorization: `Bearer ${token}` },
      })
      const payload = await readJsonSafely(response)
      if (!response.ok) {
        if (response.status === 401) handleLogout()
        throw new Error(payload?.detail || 'Could not load documents.')
      }
      setDocuments(payload?.documents || [])
    } catch (requestError) {
      const message = requestError instanceof Error ? requestError.message : 'Could not load documents.'
      setDocuments([])
      setDocumentError(message === 'Failed to fetch' ? 'The document service is unavailable right now. Please try again.' : message)
    } finally {
      setIsDocumentsLoading(false)
    }
  }

  function handleFileSelection(file) {
    if (!file) {
      setSelectedFile(null)
      setUploadStatus('idle')
      setUploadMessage('')
      setUploadProgress(0)
      return
    }

    if (!isPdfFile(file)) {
      setSelectedFile(null)
      setUploadStatus('invalid-file')
      setUploadMessage('Please choose a valid PDF file.')
      setDocumentError('')
      setUploadProgress(0)
      return
    }

    setSelectedFile(file)
    setUploadStatus('idle')
    setUploadMessage(`Selected ${file.name}`)
    setDocumentError('')
    setUploadProgress(0)
  }

  function handleFileInputChange(event) {
    const file = event.target.files?.[0] || null
    handleFileSelection(file)
  }

  function handleDropZoneDragOver(event) {
    event.preventDefault()
    if (!isUploading) {
      setUploadStatus('drag-over')
    }
  }

  function handleDropZoneDrop(event) {
    event.preventDefault()
    if (isUploading) return

    setUploadStatus('idle')
    const file = event.dataTransfer.files?.[0] || null
    handleFileSelection(file)
  }

  function handleDropZoneDragLeave(event) {
    event.preventDefault()
    if (!isUploading) {
      setUploadStatus('idle')
    }
  }

  function openFilePicker() {
    fileInputRef.current?.click()
  }

  async function uploadDocument(event) {
    event.preventDefault()
    if (!canUpload) return

    const fileToUpload = selectedFile
    if (!fileToUpload || !isPdfFile(fileToUpload)) {
      setUploadStatus('invalid-file')
      setUploadMessage('Please choose a valid PDF file.')
      setDocumentError('')
      return
    }

    const formData = new FormData()
    formData.append('file', fileToUpload)

    setIsUploading(true)
    setUploadProgress(0)
    setUploadStatus('uploading')
    setUploadMessage('')
    setDocumentError('')

    const xhr = new XMLHttpRequest()
    xhr.open('POST', `${API_BASE_URL}/documents/upload`)
    xhr.setRequestHeader('Authorization', `Bearer ${token}`)

    xhr.upload.onprogress = (event) => {
      if (event.lengthComputable) {
        const progressPercentage = Math.round((event.loaded / event.total) * 100)
        setUploadProgress(progressPercentage)
      }
    }

    xhr.onload = async () => {
      try {
        let payload = null
        try {
          payload = JSON.parse(xhr.responseText || 'null')
        } catch {
          payload = null
        }

        if (xhr.status >= 200 && xhr.status < 300) {
          setUploadProgress(100)
          setUploadStatus('success')
          setUploadMessage(`${payload?.filename || fileToUpload.name} indexed into ${payload?.chunk_count || 0} chunks.`)
          setSelectedFile(null)
          if (fileInputRef.current) {
            fileInputRef.current.value = ''
          }
          await refreshDocuments()
        } else {
          if (xhr.status === 401) handleLogout()
          const message = payload?.detail || 'Upload failed.'
          setUploadStatus('error')
          setDocumentError(message === 'Failed to fetch' ? 'The upload service is unavailable right now. Please try again.' : message)
          setUploadMessage('')
        }
      } catch (requestError) {
        setUploadStatus('error')
        setDocumentError('The upload service is unavailable right now. Please try again.')
        setUploadMessage('')
      } finally {
        setIsUploading(false)
      }
    }

    xhr.onerror = () => {
      setUploadStatus('error')
      setDocumentError('The upload service is unavailable right now. Please try again.')
      setUploadMessage('')
      setIsUploading(false)
    }

    xhr.onabort = () => {
      setUploadStatus('error')
      setDocumentError('Upload cancelled.')
      setUploadMessage('')
      setIsUploading(false)
    }

    xhr.send(formData)
  }

  async function deleteDocument(id, filename) {
    const confirmed = window.confirm(`Delete ${filename}? This will remove the file and its indexed chunks.`)
    if (!confirmed) return

    setDeletingDocument(id)
    setDocumentError('')
    setUploadMessage('')

    try {
      const response = await fetch(`${API_BASE_URL}/documents/${encodeURIComponent(id)}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${token}` },
      })
      const payload = await readJsonSafely(response)
      if (!response.ok) {
        if (response.status === 401) handleLogout()
        throw new Error(payload?.detail || 'Delete failed.')
      }
      setActiveSources(null)
      setUploadMessage(payload?.message || `${filename} deleted successfully.`)
      await refreshDocuments()
    } catch (requestError) {
      const message = requestError instanceof Error ? requestError.message : 'Delete failed.'
      setDocumentError(message === 'Failed to fetch' ? 'The delete service is unavailable right now. Please try again.' : message)
    } finally {
      setDeletingDocument('')
    }
  }

  async function sendQuestion() {
    if (!canSubmit) return

    const userQuery = query.trim()
    const historyPayload = messages.map((msg) => ({ role: msg.role, content: msg.content }))

    setQuery('')
    setIsAtBottom(true)
    setMessages((prev) => [...prev, { role: 'user', content: userQuery }])
    setIsLoading(true)
    setLoadingMessage('Searching documents and drafting an answer...')
    setError('')

    requestAnimationFrame(() => textareaRef.current?.focus())

    try {
      const response = await fetch(`${API_BASE_URL}/ask`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ query: userQuery, top_k: topK, history: historyPayload }),
      })
      const payload = await readJsonSafely(response)
      if (!response.ok) {
        if (response.status === 401) handleLogout()
        throw new Error(payload?.detail || 'The assistant could not answer right now.')
      }
      setMessages((prev) => [...prev, { role: 'assistant', content: payload?.answer || 'I could not generate a response right now.', sources: payload?.sources || [] }])
    } catch (requestError) {
      const message = requestError instanceof Error ? requestError.message : 'The assistant could not answer right now.'
      setError(message === 'Failed to fetch' ? 'The assistant is temporarily unavailable. Please try again in a moment.' : message)
      setMessages((prev) => prev.slice(0, -1))
      setQuery(userQuery)
    } finally {
      setIsLoading(false)
      requestAnimationFrame(() => textareaRef.current?.focus())
    }
  }

  async function askQuestion(event) {
    event.preventDefault()
    await sendQuestion()
  }

  function handleComposerKeyDown(event) {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault()
      sendQuestion()
    }
  }

  function applyExample(question) {
    setQuery(question)
    setError('')
    requestAnimationFrame(() => textareaRef.current?.focus())
  }

  function clearChat() {
    setMessages([])
    setActiveSources(null)
    setError('')
    requestAnimationFrame(() => textareaRef.current?.focus())
  }

  // Always render the main app shell so the Knowledge base/sidebar is visible.
  // When there is no token, show the login panel as an overlay modal.
  const showLoginOverlay = !token

  return (
    <main className="app-shell">
      <aside className="workspace-sidebar" aria-labelledby="documents-title">
        <div className="workspace-panel">
          <header className="app-header">
            <div className="brand-block">
              <span className="brand-mark" aria-hidden="true"><Icon.Mark /></span>
              <p className="eyebrow">Enterprise RAG Assistant</p>
            </div>
            <h1 className="sidebar-title">Read the record.<br />Ask the record.</h1>
            <div className="utility-row">
              <div className="status-meta">
                <div className="user-profile" title={`Logged in as ${username}`}>
                  <span className="user-dot" aria-hidden="true" />
                  <span>{username}</span>
                </div>
                <div className="status-pill" title="Backend API target">
                  {API_BASE_URL.replace(/^https?:\/\//, '')}
                </div>
              </div>
              <button onClick={handleLogout} className="logout-btn" title="Sign out"><Icon.Logout /> Sign out</button>
            </div>
          </header>

          <section className="document-manager">
            <div className="section-heading">
              <div>
                <p className="eyebrow" style={{ color: 'var(--amber)', fontSize: '11px', fontWeight: '700', letterSpacing: '0.14em', textTransform: 'uppercase', marginBottom: '4px' }}>Documents</p>
                <h2 id="documents-title" style={{ color: '#F8FAFC', fontSize: '22px', fontWeight: '700', letterSpacing: '0.4px', marginBottom: '12px', opacity: 1, visibility: 'visible', display: 'block' }}>Knowledge base</h2>
              </div>
              <button type="button" className="refresh-icon-button" onClick={refreshDocuments} disabled={isDocumentsLoading} title="Refresh documents">
                <Icon.Refresh className={isDocumentsLoading ? 'spin' : ''} />
              </button>
            </div>

            <form className="upload-form" onSubmit={uploadDocument}>
              <label htmlFor="document-upload">Upload PDF</label>
              <div
                className={`upload-dropzone ${uploadStatus}`}
                onDragOver={handleDropZoneDragOver}
                onDragEnter={handleDropZoneDragOver}
                onDragLeave={handleDropZoneDragLeave}
                onDrop={handleDropZoneDrop}
                onClick={openFilePicker}
                role="button"
                tabIndex={0}
                onKeyDown={(event) => {
                  if (event.key === 'Enter' || event.key === ' ') {
                    event.preventDefault()
                    openFilePicker()
                  }
                }}
              >
                <div className="upload-dropzone-icon" aria-hidden="true"><Icon.Upload /></div>
                <div className="upload-dropzone-copy">
                  <p className="upload-dropzone-title">
                    {uploadStatus === 'drag-over' && 'Drop your PDF here'}
                    {uploadStatus === 'uploading' && 'Uploading PDF…'}
                    {uploadStatus === 'success' && 'Upload complete'}
                    {uploadStatus === 'error' && 'Upload failed'}
                    {uploadStatus === 'invalid-file' && 'Invalid file'}
                    {uploadStatus === 'idle' && (selectedFile ? 'Ready to upload' : 'Drop a PDF here or choose a file')}
                  </p>
                  <p className="upload-dropzone-subtitle">
                    {selectedFile ? selectedFile.name : 'Choose a PDF to index into the knowledge base.'}
                  </p>
                </div>
                <div className="upload-dropzone-actions">
                  <button type="button" className="upload-choose-btn" onClick={(event) => { event.stopPropagation(); openFilePicker() }}>Choose File</button>
                  <button type="submit" className="upload-submit-btn" disabled={!canUpload}><Icon.Upload /> {isUploading ? 'Indexing...' : 'Upload & index'}</button>
                </div>
                {isUploading && (
                  <div className="upload-progress-block" aria-live="polite">
                    <div className="upload-progress-meta">
                      <span>Uploading {selectedFile?.name || 'document'}…</span>
                      <span>{uploadProgress}%</span>
                    </div>
                    <div className="upload-progress-bar">
                      <span style={{ width: `${uploadProgress}%` }} />
                    </div>
                  </div>
                )}
              </div>
              <input ref={fileInputRef} id="document-upload" type="file" accept="application/pdf,.pdf" className="upload-file-input" onChange={handleFileInputChange} />
            </form>

            {uploadStatus === 'success' && uploadMessage && <div className="success-box">{uploadMessage}</div>}
            {uploadStatus === 'error' && documentError && <div className="error-box compact" role="alert">{documentError}</div>}
            {uploadStatus === 'invalid-file' && uploadMessage && <div className="error-box compact" role="alert">{uploadMessage}</div>}
            {uploadStatus === 'idle' && !uploadMessage && !documentError && selectedFile && <div className="success-box">Selected {selectedFile.name}</div>}

            <div className="document-stats" aria-label="Document statistics">
              <span className="stat-figure"><strong>{indexedDocumentCount}</strong> indexed</span>
              <span className="stat-figure"><strong>{totalChunks}</strong> chunks</span>
            </div>

            <div className="document-list">
              {isDocumentsLoading && <p className="muted">Loading documents...</p>}
              {!isDocumentsLoading && documents.length === 0 && <p className="muted empty-hint">No PDFs uploaded yet. Add one above to start building the knowledge base.</p>}
              {documents.map((document) => (
                <article className={`document-card ${document.indexed ? 'is-indexed' : ''}`} key={document.id}>
                  <div className="document-card-body">
                    <div className="document-card-header-row">
                      <div className="document-title-block">
                        <div className="document-icon" aria-hidden="true"><Icon.Mark /></div>
                        <div className="document-info">
                          <h3 className="document-name" title={document.filename}>{document.filename}</h3>
                          <span className="document-size">{formatBytes(document.size_bytes)}</span>
                        </div>
                      </div>
                      <button type="button" className="delete-card-btn" onClick={() => deleteDocument(document.id, document.filename)} disabled={deletingDocument === document.id} title={`Delete ${document.filename}`}>
                        <Icon.Trash />
                      </button>
                    </div>
                    <div className="document-meta">
                      {document.indexed ? <span className="indexed-stamp">Indexed</span> : <span className="meta-pill">Uploaded</span>}
                      <span className="meta-pill">{document.chunk_count} chunks</span>
                      {document.pages.length > 0 && <span className="meta-pill">{document.pages.length} pages</span>}
                    </div>
                  </div>
                </article>
              ))}
            </div>
          </section>
        </div>
      </aside>

      <section className="answer-panel" aria-label="Chat Area">
        <header className="chat-header">
          <div>
            <p className="eyebrow">Transcript</p>
            <h2>Conversation log</h2>
          </div>
          <div className="chat-header-actions">
            {messages.length > 0 && <button type="button" className="ghost-button" onClick={clearChat}>Clear chat</button>}
          </div>
        </header>

        {error && <div className="error-box" role="alert">{error}</div>}

        <section className="chat-panel">
          <div className="chat-messages" ref={chatMessagesRef} onScroll={handleChatScroll}>
            {messages.length === 0 && !error && (
              <div className="empty-state">
                <p className="eyebrow">Ready</p>
                <h2>No entries in this transcript yet.</h2>
                <p>Upload a PDF, then ask a question. Follow-ups keep their context and every answer stays grounded in citations.</p>
              </div>
            )}

            {messages.map((msg, index) => (
              <div key={index} className={`chat-bubble-container ${msg.role}`}>
                <div className="chat-bubble">
                  <span className="bubble-role">{msg.role === 'user' ? 'You' : 'Assistant'}</span>
                  <div className="bubble-content">
                    {msg.role === 'assistant' ? <ReactMarkdown remarkPlugins={[remarkGfm]}>{msg.content}</ReactMarkdown> : msg.content}
                  </div>
                  {msg.role === 'assistant' && msg.sources?.length > 0 && (
                    <div className="footnote-block">
                      <div className="footnote-tabs">
                        {msg.sources.slice(0, 6).map((source, idx) => (
                          <span className="footnote-tab" key={idx} tabIndex={0}>
                            {idx + 1}
                            <span className="footnote-tooltip" role="tooltip">
                              <strong>{source.source_file || 'Unknown file'}</strong>
                              {source.page !== null && <span className="footnote-tooltip-page"> - p.{source.page}</span>}
                              <em>{source.content?.length > 130 ? `${source.content.slice(0, 130)}...` : source.content}</em>
                            </span>
                          </span>
                        ))}
                      </div>
                      <div className="citation-preview">
                        {msg.sources.slice(0, 2).map((source, idx) => (
                          <div key={idx} className="citation-item">
                            <span className="citation-index">{idx + 1}</span>
                            {source.source_file || 'Unknown File'}
                            {source.page !== null && ` - p.${source.page}`}
                          </div>
                        ))}
                      </div>
                      <button type="button" className="sources-toggle-btn" onClick={() => setActiveSources(msg.sources)}>View all references ({msg.sources.length})</button>
                    </div>
                  )}
                </div>
              </div>
            ))}

            {isLoading && (
              <div className="chat-bubble-container assistant thinking" aria-live="polite">
                <div className="chat-bubble thinking-bubble">
                  <span className="bubble-role">Assistant</span>
                  <div className="thinking-status">{loadingMessage}</div>
                  <div className="loading-skeleton" aria-hidden="true">
                    <div className="loading-line short" />
                    <div className="loading-line" />
                    <div className="loading-line medium" />
                  </div>
                  <div className="typing-indicator"><span></span><span></span><span></span></div>
                </div>
              </div>
            )}

            <div ref={chatEndRef} />
          </div>

          {!isAtBottom && messages.length > 0 && (
            <button type="button" className="jump-latest-btn" onClick={jumpToLatest}><Icon.ArrowDown /> Jump to latest</button>
          )}

          <div className="chat-composer-shell">
            <div className="example-row" aria-label="Example questions">
              {EXAMPLE_QUESTIONS.map((question) => (
                <button key={question} type="button" onClick={() => applyExample(question)}>{question}</button>
              ))}
            </div>

            <form className="question-form" onSubmit={askQuestion}>
              <div className="composer-card">
                <textarea ref={textareaRef} id="question" value={query} onChange={(event) => setQuery(event.target.value)} onKeyDown={handleComposerKeyDown} placeholder="Ask anything about your uploaded PDFs..." rows={1} />
                <div className="composer-footer">
                  <label className="top-k-control" htmlFor="top-k">
                    <span>Context chunks</span>
                    <input id="top-k" type="number" min="1" max="20" value={topK} onChange={(event) => setTopK(Number(event.target.value))} />
                  </label>
                  <div className="composer-actions">
                    <span className="composer-hint">Enter to send, Shift+Enter for newline</span>
                    <button type="submit" disabled={!canSubmit}>{isLoading ? 'Generating...' : <><Icon.Send /> Send</>}</button>
                  </div>
                </div>
              </div>
            </form>
          </div>
        </section>

        {activeSources && (
          <div className="citations-overlay" onClick={() => setActiveSources(null)}>
            <div className="citations-sheet" onClick={(e) => e.stopPropagation()}>
              <header className="sheet-header">
                <div>
                  <p className="eyebrow">Case file</p>
                  <h3>References &amp; citations</h3>
                </div>
                <button type="button" onClick={() => setActiveSources(null)} aria-label="Close references"><Icon.Close /></button>
              </header>
              <div className="sheet-content">
                {activeSources.map((source, idx) => (
                  <article className="source-card" key={idx}>
                    <header>
                      <span className="source-index">Source {idx + 1}</span>
                      <span className="source-score">Match distance {source.score.toFixed(4)}</span>
                    </header>
                    <p className="source-location">{source.source_file || 'Unknown File'}{source.page !== null && `, page ${source.page}`}</p>
                    <p className="source-text">{source.content}</p>
                  </article>
                ))}
              </div>
            </div>
          </div>
        )}
      </section>
      {showLoginOverlay && (
        <div className="login-overlay">
          <div className="login-card" role="dialog" aria-modal="true">
            <header>
              <p className="eyebrow">Enterprise RAG Assistant</p>
              <h1>Case access</h1>
              <p className="muted-login">Sign in with the shared credential - password: <strong>Admin@1234</strong></p>
            </header>
            {loginError && <div className="error-box compact" role="alert">{loginError}</div>}
            <form onSubmit={handleLogin}>
              <div className="input-group">
                <label htmlFor="username">Username</label>
                <input id="username" type="text" required value={loginUser} onChange={(e) => setLoginUser(e.target.value)} placeholder="Enter username" autoComplete="username" />
              </div>
              <div className="input-group">
                <label htmlFor="password">Password</label>
                <input id="password" type="password" required value={loginPass} onChange={(e) => setLoginPass(e.target.value)} placeholder="Enter password" autoComplete="current-password" />
              </div>
              <div style={{ display: 'flex', gap: 8 }}>
                <button type="submit">Sign in</button>
                <button type="button" onClick={() => { setLoginUser('admin'); setLoginPass('Admin@1234'); }}>Fill</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </main>
  )
}

export default App
