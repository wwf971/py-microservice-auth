import { useState, useEffect, useRef } from 'react'
import { Login, TabsOnTop, KeyValues } from '@wwf971/react-comp-misc'
import ServerStatus from './ServerStatus'
import DatabasePanel from './DatabasePanel'
import './App.css'

function App() {
  const [isLoggedIn, setIsLoggedIn] = useState(false)
  const [authToken, setAuthToken] = useState(null)
  const [users, setUsers] = useState([])
  const [config, setConfig] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [selectedToken, setSelectedToken] = useState(null)
  const [activeTab, setActiveTab] = useState('users')
  const tabsOnTopRef = useRef(null)

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

  const handleIssueToken = async (uid, username) => {
    setLoading(true)
    setError(null)
    try {
      const response = await fetch(`/manage/api/tokens/issue`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ uid })
      })

      const result = await response.json()

      if (result.code === 0) {
        fetchUsers()
      } else {
        setError(result.message || 'Failed to issue token')
      }
    } catch (err) {
      setError('Error issuing token: ' + err.message)
    } finally {
      setLoading(false)
    }
  }

  const handleViewToken = async (jti) => {
    setLoading(true)
    setError(null)
    try {
      const response = await fetch(`/manage/api/tokens/${jti}`, {
        headers: {
          'Content-Type': 'application/json',
        }
      })

      const result = await response.json()

      if (result.code === 0) {
        setSelectedToken(result.data)
        // Switch to JWT Tokens tab
        if (tabsOnTopRef.current) {
          tabsOnTopRef.current.switchTab('jwt tokens')
        }
      } else {
        setError(result.message || 'Failed to fetch token')
      }
    } catch (err) {
      setError('Error fetching token: ' + err.message)
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
    // Clear token from localStorage
    localStorage.removeItem('authToken')
  }

  if (!isLoggedIn) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'flex-start', minHeight: '100vh', background: '#f5f5f5' }}>
        <div style={{ minWidth: '10px', height: '200px' }}></div>
        <Login 
          title="Management Login"
          loginEndpoint="/manage/login"
          timeout={5000}
          onSuccess={handleLoginSuccess}
          useAuthToken={true}
          authTokenKey="authToken"
          showTokenAtLogin={true}
        />
      </div>
    )
  }

  return (
    <div className="dashboard">
      <header className="dashboard-header">
        <div style={{ padding: '0px 16px'}}>
          <h1>User Management Dashboard</h1>
          <button onClick={handleLogout} className="logout-btn">Logout</button>
        </div>
      </header>

      <main className="dashboard-content">
        <ServerStatus />
        
        <div className="tabs-wrapper">
          <TabsOnTop ref={tabsOnTopRef} defaultTab="users">
            <TabsOnTop.Tab label="Users">


              {error && <div className="error-message">{error}</div>}

              <div className="table-container">
                <table className="users-table">
                  <thead>
                    <tr>
                      <th>UID</th>
                      <th>Username</th>
                      <th>Password Hash</th>
                      <th>JWT Tokens</th>
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
                                  <button
                                    key={idx}
                                    className="token-info-btn"
                                    title={jti}
                                    onClick={() => handleViewToken(jti)}
                                  >
                                    {jti.substring(0, 8)}...
                                  </button>
                                ))}
                              </div>
                            ) : (
                              <button 
                                className="action-btn issue-btn"
                                onClick={() => handleIssueToken(user.uid, user.username)}
                                disabled={loading}
                              >
                                Issue
                              </button>
                            )}
                          </td>
                          <td>
                            <button 
                              onClick={() => handleDeleteUser(user.uid, user.username)}
                              className="action-btn delete-btn"
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
              <div className="section-header">
                <div className="action-buttons">
                  <button onClick={handleCreateUser} className="create-btn" disabled={loading}>
                    Create User
                  </button>
                  <button onClick={fetchUsers} className="refresh-btn" disabled={loading}>
                    {loading ? 'Loading...' : 'Refresh'}
                  </button>
                </div>
              </div>
          </TabsOnTop.Tab>

          <TabsOnTop.Tab label="JWT Tokens">
            <div className="section-header">
              <h2>JWT Token Details</h2>
            </div>
            {selectedToken ? (
              <div className="token-details">
                <KeyValues
                  data={Object.entries(selectedToken).map(([key, value]) => ({
                    key,
                    value: typeof value === 'object' ? JSON.stringify(value) : String(value)
                  }))}
                  isEditable={false}
                  alignColumn={true}
                  keyColWidth="min"
                />
              </div>
            ) : (
              <div className="no-token-selected">
                Select a token from the Users table to view its details
              </div>
            )}
          </TabsOnTop.Tab>

          <TabsOnTop.Tab label="Databases">
            <DatabasePanel />
          </TabsOnTop.Tab>
        </TabsOnTop>
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
