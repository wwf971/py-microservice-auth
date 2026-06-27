import { useEffect } from 'react'
import { observer } from 'mobx-react-lite'
import { EndpointCard } from '@wwf971/react-comp-misc'
import { manageStore } from './store'
import './DbPanel.css'

function DbPanel() {
  useEffect(() => {
    manageStore.fetchDbs()
  }, [])

  const getDbCardData = (db) => ({
    id: String(db.id),
    titleText: db.name || `db-${db.id}`,
    descriptionText: db.type === 'sqlite' ? (db.path || '') : `${db.host || ''}:${db.port || ''}`,
    statusTagText: db.id === manageStore.dbCurrentId ? 'Current' : '',
    statusMessage: manageStore.dbStatusMessageById[db.id] || null,
    keyValues: [
      { key: 'type', value: db.type || '' },
      { key: 'db', value: db.database || db.path || '' },
      { key: 'user', value: db.username || '' },
    ],
  })

  return (
    <div className="db-panel">
      <div className="section-header">
        <div className="section-title">Db Endpoints</div>
        <div className="action-buttons">
          <button onClick={manageStore.fetchDbs} className="action-btn" disabled={manageStore.isLoading}>
            Refresh
          </button>
        </div>
      </div>

      {manageStore.dbError && <div className="error-message">{manageStore.dbError}</div>}

      <div className="db-card-list">
        {manageStore.dbs.map((db) => (
          <EndpointCard
            key={db.id}
            data={getDbCardData(db)}
            config={{
              isSelected: db.id === manageStore.dbSelectedId,
              isSelectable: true,
              isLocked: manageStore.isLoading,
              keyColWidth: '72px',
              actionItems: [
                {
                  id: 'test',
                  labelText: 'Test',
                  isDisabled: manageStore.isLoading,
                },
                {
                  id: 'switch',
                  labelText: 'Switch',
                  isVisible: db.id !== manageStore.dbCurrentId,
                  isDisabled: manageStore.isLoading,
                },
                {
                  id: 'remove',
                  labelText: 'Remove',
                  isVisible: db.is_removable === true,
                  isDisabled: manageStore.isLoading,
                  isDanger: true,
                },
              ],
            }}
            onEvent={(eventType, eventData) => {
              if (eventType === 'select') {
                manageStore.selectDb(db.id)
              }
              if (eventType === 'action' && eventData.actionId === 'test') {
                manageStore.testDb(db.id)
              }
              if (eventType === 'action' && eventData.actionId === 'switch') {
                manageStore.switchDb(db.id)
              }
              if (eventType === 'action' && eventData.actionId === 'remove') {
                manageStore.removeDb(db.id)
              }
              if (eventType === 'dismissStatusMessage') {
                manageStore.dismissDbStatusMessage(db.id)
              }
            }}
          />
        ))}
      </div>
    </div>
  )
}

export default observer(DbPanel)
