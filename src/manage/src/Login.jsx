import { useState } from 'react'
import './Login.css'

function Login() {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [message, setMessage] = useState('')
  const [loading, setLoading] = useState(false)

  const handleLogin = async (e) => {
    e.preventDefault()
    setLoading(true)
    setMessage('')

    try {
      // Create an AbortController for timeout
      const controller = new AbortController()
      const timeoutId = setTimeout(() => controller.abort(), 5000) // 5 second timeout

      const response = await fetch('/manage/login', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ username, password }),
        signal: controller.signal,
      })

      clearTimeout(timeoutId)

      const data = await response.json()

      if (data.code === 0) {
        setMessage('✓ Login successful!')
        // Store token and redirect or update UI
        localStorage.setItem('authToken', data.data.token)
      } else {
        setMessage(`✗ ${data.message}`)
      }
    } catch (error) {
      if (error.name === 'AbortError') {
        setMessage('✗ Server not responding. Please check if the server is running.')
      } else {
        setMessage(`✗ Error: ${error.message}`)
      }
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="login-container">
      <div className="login-box">
        <h1>Management Login</h1>
        <form onSubmit={handleLogin}>
          <div className="form-group">
            <label htmlFor="username">Username(Administrator):</label>
            <input
              type="text"
              id="username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
              disabled={loading}
            />
          </div>
          <div className="form-group">
            <label htmlFor="password">Password(Administrator):</label>
            <input
              type="password"
              id="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              disabled={loading}
            />
          </div>
          <button type="submit" disabled={loading}>
            {loading ? 'Logging in...' : 'Login'}
          </button>
        </form>
        {message && <div className={`message ${message.startsWith('✓') ? 'success' : 'error'}`}>{message}</div>}
      </div>
    </div>
  )
}

export default Login
