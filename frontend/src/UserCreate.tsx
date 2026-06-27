import { observer } from 'mobx-react-lite'
import { manageStore } from './store'

function UserCreate() {
  if (manageStore.popupCurrent !== 'user-create') return null

  return (
    <div className="popup-backdrop">
      <div className="popup-panel">
        <div className="popup-title">Create User</div>
        <div className="popup-content">
          <label className="popup-field">
            <span className="popup-field-label">Username</span>
            <input
              className="text-input popup-input"
              value={manageStore.userDraft.username}
              onChange={(event) => manageStore.setUserDraftField('username', event.target.value)}
              autoFocus
            />
          </label>
          <label className="popup-field">
            <span className="popup-field-label">Password</span>
            <input
              className="text-input popup-input"
              value={manageStore.userDraft.password}
              onChange={(event) => manageStore.setUserDraftField('password', event.target.value)}
              type="password"
            />
          </label>
        </div>
        <div className="popup-actions">
          <button type="button" className="action-btn" onClick={manageStore.closePopup} disabled={manageStore.isLoading}>
            Cancel
          </button>
          <button type="button" className="action-btn action-btn-primary" onClick={manageStore.createUser} disabled={manageStore.isLoading}>
            Create
          </button>
        </div>
      </div>
    </div>
  )
}

export default observer(UserCreate)
