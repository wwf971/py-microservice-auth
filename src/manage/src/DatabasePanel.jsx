import { useState, useEffect } from 'react'
import { KeyValues } from '@wwf971/react-comp-misc'
import './DatabasePanel.css'

function DatabasePanel() {
  const [databases, setDatabases] = useState([])
  const [currentDbId, setCurrentDbId] = useState(0)
  const [selectedDb, setSelectedDb] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const fetchDatabases = async () => {
    setLoading(true)
    setError(null)
    try {
      const response = await fetch('/manage/api/databases')
      const result = await response.json()
      
      if (result.code === 0) {
        setDatabases(result.data.databases)
        setCurrentDbId(result.data.current_database_id)
      } else {
        setError(result.message || 'Failed to fetch databases')
      }
    } catch (err) {
      setError('Error fetching databases: ' + err.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchDatabases()
  }, [])

  const handleSelectDatabase = (db) => {
    setSelectedDb(db)
  }

  const handleSwitchDatabase = async (dbId) => {
    setLoading(true)
    setError(null)
    try {
      const response = await fetch(`/manage/api/databases/switch/${dbId}`, {
        method: 'POST'
      })
      const result = await response.json()
      
      if (result.code === 0) {
        fetchDatabases()
      } else {
        setError(result.message || 'Failed to switch database')
      }
    } catch (err) {
      setError('Error switching database: ' + err.message)
    } finally {
      setLoading(false)
    }
  }

  const handleAddDatabase = () => {
    const name = prompt('Enter database name:')
    if (!name) return

    const type = prompt('Enter database type (sqlite/postgresql/mysql):')
    if (!type) return

    const data = { name, type }

    if (type.toLowerCase() === 'sqlite') {
      const path = prompt('Enter SQLite file path:')
      if (path) data.path = path
    } else {
      const host = prompt('Enter host:')
      const port = prompt('Enter port:')
      const database = prompt('Enter database name:')
      const username = prompt('Enter username:')
      const password = prompt('Enter password:')
      
      if (host) data.host = host
      if (port) data.port = parseInt(port)
      if (database) data.database = database
      if (username) data.username = username
      if (password) data.password = password
    }

    addDatabase(data)
  }

  const addDatabase = async (data) => {
    setLoading(true)
    setError(null)
    try {
      const response = await fetch('/manage/api/databases', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(data)
      })
      const result = await response.json()
      
      if (result.code === 0) {
        fetchDatabases()
      } else {
        setError(result.message || 'Failed to add database')
      }
    } catch (err) {
      setError('Error adding database: ' + err.message)
    } finally {
      setLoading(false)
    }
  }

  const handleRemoveDatabase = async (dbId) => {
    setLoading(true)
    setError(null)
    try {
      const response = await fetch(`/manage/api/databases/${dbId}`, {
        method: 'DELETE'
      })
      const result = await response.json()
      
      if (result.code === 0) {
        setSelectedDb(null)
        fetchDatabases()
      } else {
        setError(result.message || 'Failed to remove database')
      }
    } catch (err) {
      setError('Error removing database: ' + err.message)
    } finally {
      setLoading(false)
    }
  }

  const formatDbForDisplay = (db) => {
    const data = [
      { key: 'ID', value: db.id.toString() },
      { key: 'Name', value: db.name },
      { key: 'Type', value: db.type },
    ]

    if (db.type === 'sqlite') {
      data.push({ key: 'Path', value: db.path || 'N/A' })
    } else {
      data.push({ key: 'Host', value: db.host || 'N/A' })
      data.push({ key: 'Port', value: db.port ? db.port.toString() : 'N/A' })
      data.push({ key: 'Database', value: db.database || 'N/A' })
      data.push({ key: 'Username', value: db.username || 'N/A' })
      data.push({ key: 'Password', value: db.password ? '••••••••' : 'N/A' })
    }

    data.push({ key: 'Is Default', value: db.is_default ? 'Yes' : 'No' })
    data.push({ key: 'Removable', value: db.is_removable ? 'Yes' : 'No' })

    return data
  }

  return (
    <div className="database-panel">
      <div className="database-list-section">
        <div className="section-header">
          <h2>Database Connections</h2>
          <div className="action-buttons">
            <button onClick={handleAddDatabase} className="action-btn" disabled={loading}>
              Add Database
            </button>
            <button onClick={fetchDatabases} className="action-btn" disabled={loading}>
              {loading ? 'Loading...' : 'Refresh'}
            </button>
          </div>
        </div>

        {error && <div className="error-message">{error}</div>}

        <div className="database-list">
          {databases.map((db) => (
            <div
              key={db.id}
              className={`database-item ${db.id === currentDbId ? 'active' : ''} ${selectedDb?.id === db.id ? 'selected' : ''}`}
              onClick={() => handleSelectDatabase(db)}
            >
              <div className="database-item-header">
                <span className="database-name">{db.name}</span>
                {db.id === currentDbId && <span className="current-badge">Current</span>}
              </div>
              <div className="database-item-info">
                <span className="database-type">{db.type}</span>
                {db.type === 'sqlite' ? (
                  <span className="database-detail">{db.path}</span>
                ) : (
                  <span className="database-detail">{db.host}:{db.port}</span>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="database-details-section">
        <div className="section-header">
          <h2>Database Details</h2>
          {selectedDb && (
            <div className="action-buttons">
              {selectedDb.id !== currentDbId && (
                <button
                  onClick={() => handleSwitchDatabase(selectedDb.id)}
                  className="action-btn switch-btn"
                  disabled={loading}
                >
                  Switch to This
                </button>
              )}
              {selectedDb.is_removable && (
                <button
                  onClick={() => handleRemoveDatabase(selectedDb.id)}
                  className="action-btn delete-btn"
                  disabled={loading}
                >
                  Remove
                </button>
              )}
            </div>
          )}
        </div>

        {selectedDb ? (
          <KeyValues
            data={formatDbForDisplay(selectedDb)}
            isEditable={false}
            alignColumn={true}
            keyColWidth="min"
          />
        ) : (
          <div className="no-selection">
            Select a database from the list to view details
          </div>
        )}
      </div>
    </div>
  )
}

export default DatabasePanel

