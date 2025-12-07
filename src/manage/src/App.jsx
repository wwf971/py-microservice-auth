import { useState, useEffect } from 'react'
import { Login } from '@wwf971/react-comp-misc'
import './App.css'

function App() {
  const [isLoggedIn, setIsLoggedIn] = useState(false)
  const [authToken, setAuthToken] = useState(null)
  const [users, setUsers] = useState([])
  const [config, setConfig] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [selectedUser, setSelectedUser] = useState(null)

  const handleLoginSuccess = (data) => {
    console.log('Login successful:', data)
    setAuthToken(data.token)
    setIsLoggedIn(true)
  }

  const fetchUsers = async () => {
    setLoading(true)
    setError(null)
    try {
      const response = await fetch('/manage/api/users', {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      })
      const result = await response.json()
      
      if (result.code === 0) {
        setUsers(result.data.users || [])
      } else {
        setError(result.message || 'Failed to fetch users')
      }
    } catch (err) {
      setError('Error fetching users: ' + err.message)
    } finally {
      setLoading(false)
    }
  }

  const fetchConfig = async () => {
    try {
      const response = await fetch('/manage/api/config', {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      })
      const result = await response.json()
      
      if (result.code === 0) {
        setConfig(result.data.config || {})
      }
    } catch (err) {
      console.error('Error fetching config:', err)
    }
  }

  const handleCreateUser = async () => {
    const username = prompt('Enter username:')
    if (!username) return
    
    const password = prompt('Enter password:')
    if (!password) return
    
    setLoading(true)
    setError(null)
    try {
      const response = await fetch('/manage/api/users', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ username, password }),
      })
      const result = await response.json()
      
      if (result.code === 0) {
        alert(`User created successfully! UID: ${result.data.uid}`)
        fetchUsers()
      } else {
        setError(result.message || 'Failed to create user')
      }
    } catch (err) {
      setError('Error creating user: ' + err.message)
    } finally {
      setLoading(false)
    }
  }

  const handleDeleteUser = async (uid, username) => {
    if (!confirm(`Are you sure you want to delete user '${username}' (UID: ${uid})?`)) {
      return
    }
    
    setLoading(true)
    setError(null)
    try {
      const response = await fetch(`/manage/api/users/${uid}`, {
        method: 'DELETE',
        headers: {
          'Content-Type': 'application/json',
        },
      })
      const result = await response.json()
      
      if (result.code === 0) {
        alert('User deleted successfully!')
        fetchUsers()
      } else {
        setError(result.message || 'Failed to delete user')
      }
    } catch (err) {
      setError('Error deleting user: ' + err.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (isLoggedIn) {
      fetchUsers()
      fetchConfig()
    }
  }, [isLoggedIn])

  const handleLogout = () => {
    setIsLoggedIn(false)
    setAuthToken(null)
    setUsers([])
  }

  if (!isLoggedIn) {
    return (
      <Login 
        loginEndpoint="/manage/login"
        timeout={5000}
        onSuccess={handleLoginSuccess}
        useAuthToken={true}
        authTokenKey="authToken"
        showTokenAtLogin={true}
      />
    )
  }

  return (
    <div className="dashboard">
      <header className="dashboard-header">
        <h1>User Management Dashboard</h1>
        <button onClick={handleLogout} className="logout-btn">Logout</button>
      </header>

      <main className="dashboard-content">
        <div className="section-header">
          <h2>Users</h2>
          <div className="action-buttons">
            <button onClick={handleCreateUser} className="create-btn" disabled={loading}>
              Create User
            </button>
            <button onClick={fetchUsers} className="refresh-btn" disabled={loading}>
              {loading ? 'Loading...' : 'Refresh'}
            </button>
          </div>
        </div>

        {error && <div className="error-message">{error}</div>}

        <div className="table-container">
          <table className="users-table">
            <thead>
              <tr>
                <th>UID</th>
                <th>Username</th>
                <th>Password Hash</th>
                <th>JWT Token IDs</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {users.length === 0 ? (
                <tr>
                  <td colSpan="5" className="no-data">No users found</td>
                </tr>
              ) : (
                users.map((user) => (
                  <tr key={user.uid}>
                    <td>{user.uid}</td>
                    <td>{user.username}</td>
                    <td className="password-hash">{user.password_hash}</td>
                    <td className="token-ids">
                      {user.jwt_token_ids.length > 0 ? (
                        <div className="token-list">
                          {user.jwt_token_ids.map((jti, idx) => (
                            <span key={idx} className="token-id" title={jti}>
                              {jti.substring(0, 8)}...
                            </span>
                          ))}
                        </div>
                      ) : (
                        <span className="no-tokens">No active tokens</span>
                      )}
                    </td>
                    <td>
                      <button 
                        onClick={() => handleDeleteUser(user.uid, user.username)}
                        className="delete-btn"
                        disabled={loading}
                      >
                        Delete
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        <div className="config-panel">
          <h2>Configuration</h2>
          <div className="config-container">
            {config ? (
              <pre className="config-json">{JSON.stringify(config, null, 2)}</pre>
            ) : (
              <p>Loading configuration...</p>
            )}
          </div>
        </div>
      </main>
    </div>
  )
}

export default App
