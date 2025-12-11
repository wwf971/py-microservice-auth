import { useAtom } from 'jotai'
import { serverState } from './store'
import './ServerStatus.css'

function ServerStatusPanel({ serverKey }) {
  const [server, setServer] = useAtom(serverState[serverKey])

  const checkServerStatus = async () => {
    try {
      const response = await fetch(`/manage/api/server_status/${server.name}`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      })
      const result = await response.json()

      if (result.code === 0) {
        setServer({
          ...server,
          isAlive: result.data.is_alive,
          port: result.data.port,
          lastChecked: new Date().toISOString(),
        })
      } else {
        setServer({
          ...server,
          isAlive: false,
          lastChecked: new Date().toISOString(),
        })
      }
    } catch (err) {
      setServer({
        ...server,
        isAlive: false,
        lastChecked: new Date().toISOString(),
      })
    }
  }

  const getStatusColor = () => {
    if (server.isAlive === null) return '#999'
    return server.isAlive ? '#27ae60' : '#e74c3c'
  }

  const getStatusText = () => {
    if (server.isAlive === null) return 'Unknown'
    return server.isAlive ? 'Alive' : 'Down'
  }

  return (
    <div className="server-panel">
      <div className="server-name">{server.name.toUpperCase()} Server</div>
      <div className="server-info">
        <div className="server-row">
          <span className="label">Port:</span>
          <span className="value">{server.port}</span>
        </div>
        <div className="server-row">
          <span className="label">Status:</span>
          <span className="value" style={{ color: getStatusColor() }}>
            {getStatusText()}
          </span>
          <button onClick={checkServerStatus} className="renew-btn">
            Renew
          </button>
        </div>
      </div>
    </div>
  )
}

function ServerStatus() {
  return (
    <div className="server-status-container">
      <h2>Server Status</h2>
      <div className="server-panels">
        <ServerStatusPanel serverKey="aux" />
        <ServerStatusPanel serverKey="grpc" />
        <ServerStatusPanel serverKey="http" />
      </div>
    </div>
  )
}

export default ServerStatus

