import { Component } from 'react'

/**
 * Top-level error boundary.
 * Catches unhandled render errors so the app shows a recovery message
 * instead of a blank white screen.
 */
export default class ErrorBoundary extends Component {
  constructor(props) {
    super(props)
    this.state = { hasError: false }
  }

  static getDerivedStateFromError() {
    return { hasError: true }
  }

  componentDidCatch(error, info) {
    // Log to console only — never expose to users
    console.error('[ErrorBoundary] Unhandled render error:', error, info)
  }

  render() {
    if (this.state.hasError) {
      return (
        <div style={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          height: '100vh',
          gap: '12px',
          fontFamily: 'system-ui, sans-serif',
          color: '#94a3b8',
          background: '#0f172a',
        }}>
          <h2 style={{ color: '#f8fafc', margin: 0 }}>Something went wrong</h2>
          <p style={{ margin: 0 }}>Please refresh the page to continue.</p>
          <button
            onClick={() => window.location.reload()}
            style={{
              marginTop: '8px',
              padding: '10px 20px',
              background: '#f59e0b',
              color: '#0f172a',
              border: 'none',
              borderRadius: '8px',
              fontWeight: '700',
              cursor: 'pointer',
            }}
          >
            Refresh page
          </button>
        </div>
      )
    }
    return this.props.children
  }
}
