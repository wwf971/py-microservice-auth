import { useEffect, useRef } from 'react'
import { observer } from 'mobx-react-lite'
import { ButtonWithDropDown, Login, TabsOnTop, FolderView } from '@wwf971/react-comp-misc'
import ServerStatusCard from './ServerStatusCard'
import DbPanel from './DbPanel'
import UserCreate from './UserCreate'
import UserPermissionEdit from './UserPermissionEdit'
import ServicePermissionCreate from './ServicePermissionCreate'
import ConfigManagePanel from './ConfigManagePanel'
import { manageStore } from './store'
import './App.css'

function UserUsernameCell({ data }) {
  const usernameText = typeof data === 'object' && data !== null ? String(data.text || '') : String(data || '')
  const isCurrentUser = typeof data === 'object' && data !== null && data.isCurrentUser === true

  return (
    <div className="table-text-cell user-username-cell">
      <span className="user-username-text">{usernameText}</span>
      {isCurrentUser ? <span className="auth-current-user-tag">current</span> : null}
    </div>
  )
}

function UserTokenCountCell({ data, rowId, onEvent }) {
  const handleDoubleClick = (event) => {
    event.preventDefault()
    event.stopPropagation()
    onEvent?.('userTokenCountDoubleClick', { rowId })
  }

  return (
    <div
      className="table-text-cell table-link-cell table-link-cell-fill"
      data-user-token-count-cell
      onDoubleClick={handleDoubleClick}
    >
      {data}
    </div>
  )
}

function TimeCell({ data }) {
  return (
    <div className="table-text-cell" title={data?.title || ''}>
      {data?.text || ''}
    </div>
  )
}

function TokenUsernameCell({ data, rowId, onEvent }) {
  const handleDoubleClick = (event) => {
    event.preventDefault()
    event.stopPropagation()
    onEvent?.('tokenUsernameDoubleClick', { rowId })
  }

  return (
    <div className="table-text-cell table-link-cell" onDoubleClick={handleDoubleClick}>
      {data}
    </div>
  )
}

function App() {
  const tabsOnTopRef = useRef(null)

  useEffect(() => {
    if (manageStore.isLoggedIn) {
      manageStore.bootstrap()
    }
  }, [manageStore.isLoggedIn])

  const handleTokenView = async (jti) => {
    await manageStore.viewToken(jti)
    if (tabsOnTopRef.current) {
      tabsOnTopRef.current.switchTab('jwt tokens')
    }
  }

  const handleSelectedTokenView = async () => {
    const jti = manageStore.userSelected?.jwt_token_ids?.[0]
    if (jti) {
      await handleTokenView(jti)
    }
  }

  const navigateToUserTokens = () => {
    tabsOnTopRef.current?.switchTab('jwt tokens')
    const tokenIds = manageStore.userSelected?.jwt_token_ids || []
    if (tokenIds.length > 0) {
      manageStore.tokenSelectedJti = tokenIds[0]
    }
  }

  const handleUserFolderEvent = (eventType, eventData) => {
    const result = manageStore.handleUserFolderEvent(eventType, eventData)
    if (
      result?.intent === 'viewUserTokens'
      || (
        eventType === 'rowContextMenuItemClick'
        && eventData.item?.id === 'view_tokens'
      )
    ) {
      navigateToUserTokens()
    }
    return result
  }

  const handleTokenFolderEvent = (eventType, eventData) => {
    const result = manageStore.handleTokenFolderEvent(eventType, eventData)
    if (
      (
        eventType === 'tokenUsernameDoubleClick'
        || (
          eventType === 'rowContextMenuItemClick'
          && eventData.item?.id === 'view_user'
        )
      )
      && tabsOnTopRef.current
    ) {
      tabsOnTopRef.current.switchTab('users')
    }
    return result
  }

  if (!manageStore.isLoggedIn) {
    return (
      <div className="login-page">
        <div className="login-spacer" />
        <Login 
          data={manageStore}
          title="Auth(Jwt) Management Console"
          onDataChangeRequest={manageStore.onDataChangeRequest}
          useAuthToken={true}
          showTokenAtLogin={true}
        />
      </div>
    )
  }

  return (
    <div className="dashboard">
      <UserCreate />
      <UserPermissionEdit />
      <ServicePermissionCreate />
      <header className="dashboard-header">
        <div className="dashboard-header-inner">
          <div className="page-title">User Management Dashboard</div>
          <button onClick={manageStore.logout} className="logout-btn">Logout</button>
        </div>
      </header>

      <main className="dashboard-content">
        <ServerStatusCard />
        <DbPanel />
        
        <div className="tabs-wrapper">
          <TabsOnTop ref={tabsOnTopRef} defaultTab="users" autoSwitchToNewTab={false}>
            <TabsOnTop.Tab label="Users">
              {manageStore.error && <div className="error-message">{manageStore.error}</div>}
              <div className="user-panel">
                <div className="user-panel-title-row">
                  <div className="section-title">Users</div>
                  <div className="user-selected-text">
                    {manageStore.userSelected ? `Selected: ${manageStore.userSelected.username}` : 'No user selected'}
                  </div>
                </div>
                <div className="user-control-row">
                  <button type="button" className="action-btn" onClick={() => manageStore.openPopup('user-create')} disabled={manageStore.isUserFolderLocked}>
                    Create User
                  </button>
                  <button type="button" className="action-btn" onClick={() => manageStore.openPopup('permission-edit')} disabled={manageStore.isUserActionDisabled}>
                    Edit Permissions
                  </button>
                  <button type="button" className="action-btn" onClick={() => manageStore.openPopup('service-permission-create')} disabled={manageStore.isUserFolderLocked}>
                    Declare Service Permission
                  </button>
                  <button type="button" className="action-btn" onClick={() => manageStore.issueToken(manageStore.userSelected.uid)} disabled={manageStore.isUserActionDisabled}>
                    Issue Token
                  </button>
                  <button
                    type="button"
                    className="action-btn"
                    onClick={handleSelectedTokenView}
                    disabled={manageStore.isUserActionDisabled || !manageStore.userSelected?.jwt_token_ids?.length}
                  >
                    View Token
                  </button>
                  <button type="button" className="action-btn delete-btn" onClick={() => manageStore.deleteUser(manageStore.userSelected.uid)} disabled={manageStore.isUserActionDisabled}>
                    Delete User
                  </button>
                  <button type="button" className="action-btn" onClick={manageStore.fetchUsers} disabled={manageStore.isUserFolderLocked}>
                    {manageStore.isLoading ? 'Loading...' : 'Refresh'}
                  </button>
                </div>
                <FolderView
                  data={manageStore.userFolderData}
                  config={{
                    ...manageStore.userFolderConfig,
                    compBodyByColId: (colId) => {
                      if (colId === 'username') return UserUsernameCell
                      if (colId === 'tokenCount') return UserTokenCountCell
                      return undefined
                    },
                  }}
                  onEvent={handleUserFolderEvent}
                />
              </div>
          </TabsOnTop.Tab>

          <TabsOnTop.Tab label="JWT Tokens">
            <div className="user-panel">
              <div className="user-panel-title-row">
                <div className="section-title">JWT Tokens</div>
                <div className="user-selected-text">
                  {manageStore.tokenSelectedJti ? `Selected: ${manageStore.tokenSelectedJti}` : 'No token selected'}
                </div>
              </div>
              <div className="user-control-row">
                <button
                  type="button"
                  className="action-btn"
                  onClick={() => manageStore.issueToken(manageStore.uidForTokenIssue)}
                  disabled={manageStore.isLoading || !manageStore.uidForTokenIssue}
                >
                  Add Token
                </button>
                <button
                  type="button"
                  className="action-btn"
                  onClick={() => manageStore.viewToken(manageStore.tokenSelectedJti)}
                  disabled={manageStore.isTokenActionDisabled}
                >
                  View Token
                </button>
                <button
                  type="button"
                  className="action-btn delete-btn"
                  onClick={() => manageStore.revokeToken(manageStore.tokenSelectedJti)}
                  disabled={manageStore.isTokenActionDisabled}
                >
                  Revoke Token
                </button>
                <button
                  type="button"
                  className="action-btn delete-btn"
                  onClick={() => manageStore.deleteToken(manageStore.tokenSelectedJti)}
                  disabled={manageStore.isTokenActionDisabled}
                >
                  Delete Token
                </button>
                <button
                  type="button"
                  className="action-btn"
                  title="Check valid tokens and mark tokens as expired when their expiration time has passed."
                  onClick={manageStore.checkExpiredTokens}
                  disabled={manageStore.isLoading}
                >
                  Check Expired
                </button>
                <ButtonWithDropDown
                  data={{
                    label: 'Remove Tokens',
                    items: [
                      { id: 'expired', label: 'Expired' },
                      { id: 'revoked', label: 'Revoked' },
                      { id: 'expired_revoked', label: 'Expired + Revoked' },
                    ],
                  }}
                  config={{
                    isDisabled: manageStore.isLoading,
                    buttonClassName: 'action-btn',
                    title: 'Remove expired tokens, revoked tokens, or both from the token table.',
                    minWidth: 150,
                  }}
                  onEvent={(_eventType, eventData) => manageStore.removeTokensByStatus(eventData?.item?.id)}
                />
                <button type="button" className="action-btn" onClick={manageStore.fetchUsers} disabled={manageStore.isLoading}>
                  {manageStore.isLoading ? 'Loading...' : 'Refresh'}
                </button>
              </div>
              <FolderView
                data={manageStore.tokenFolderData}
                config={{
                  ...manageStore.tokenFolderConfig,
                  compBodyByColId: (colId) => {
                    if (colId === 'username') return TokenUsernameCell
                    if (colId === 'createdAt' || colId === 'expiresAt') return TimeCell
                    return undefined
                  },
                }}
                onEvent={handleTokenFolderEvent}
              />
            </div>
          </TabsOnTop.Tab>

        </TabsOnTop>
        </div>

        <ConfigManagePanel />
      </main>
    </div>
  )
}

export default observer(App)
