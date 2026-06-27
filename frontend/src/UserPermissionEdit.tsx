import { observer } from 'mobx-react-lite'
import React, { useEffect } from 'react'
import { manageStore } from './store'

function UserPermissionEdit() {
  const user = manageStore.userSelected
  useEffect(() => {
    if (manageStore.popupCurrent === 'permission-edit' && user) {
      manageStore.markPermissionPanelReady()
    }
  }, [user])

  if (manageStore.popupCurrent !== 'permission-edit' || !user) return null

  return (
    <div className="popup-backdrop">
      <div className="popup-panel popup-panel-wide">
        <div className="popup-title">Edit Permissions: {user.username}</div>
        <div className="popup-content">
          <div className="popup-subtitle">Built-in Permissions</div>
          <div className="popup-chip-list">
            {manageStore.permissions.map((permission) => (
              <button
                key={permission.permission_code}
                type="button"
                className={manageStore.isPermissionDraftAssigned(permission.permission_code) ? 'permission-chip permission-chip-active' : 'permission-chip'}
                onClick={() => manageStore.togglePermissionDraft(permission.permission_code)}
                disabled={manageStore.isLoading}
                title={permission.description}
              >
                {permission.display_name} ({permission.permission_code})
              </button>
            ))}
          </div>
          <div className="popup-subtitle">Service Permissions</div>
          <div className="popup-chip-list">
            {manageStore.servicePermissions.length === 0 ? (
              <div className="popup-empty-text">No service permission declared.</div>
            ) : (
              manageStore.servicePermissions.map((permission) => (
                <button
                  key={`${permission.service_id}-${permission.permission_code}`}
                  type="button"
                  className={manageStore.isServicePermissionDraftAssigned(permission) ? 'permission-chip permission-chip-active' : 'permission-chip'}
                  onClick={() => manageStore.toggleServicePermissionDraft(permission)}
                  disabled={manageStore.isLoading}
                  title={permission.description}
                >
                  {permission.service_id}::{permission.permission_code}
                </button>
              ))
            )}
          </div>
        </div>
        <div className="popup-actions">
          <button type="button" className="action-btn" onClick={manageStore.closePopup} disabled={manageStore.isLoading}>
            Cancel
          </button>
          <button type="button" className="action-btn action-btn-primary" onClick={manageStore.savePermissionDraft} disabled={manageStore.isLoading}>
            Save
          </button>
        </div>
      </div>
    </div>
  )
}

export default observer(UserPermissionEdit)
