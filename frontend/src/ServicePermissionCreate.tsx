import { observer } from 'mobx-react-lite'
import { manageStore } from './store'

function ServicePermissionCreate() {
  if (manageStore.popupCurrent !== 'service-permission-create') return null

  return (
    <div className="popup-backdrop">
      <div className="popup-panel">
        <div className="popup-title">Declare Service Permission</div>
        <div className="popup-content">
          <label className="popup-field">
            <span className="popup-field-label">Service Id</span>
            <input
              className="text-input popup-input"
              value={manageStore.servicePermissionDraft.service_id}
              onChange={(event) => manageStore.setServicePermissionDraftField('service_id', event.target.value)}
              autoFocus
            />
          </label>
          <label className="popup-field">
            <span className="popup-field-label">Permission Code</span>
            <input
              className="text-input popup-input"
              value={manageStore.servicePermissionDraft.permission_code}
              onChange={(event) => manageStore.setServicePermissionDraftField('permission_code', event.target.value)}
            />
          </label>
          <label className="popup-field">
            <span className="popup-field-label">Display Name</span>
            <input
              className="text-input popup-input"
              value={manageStore.servicePermissionDraft.display_name}
              onChange={(event) => manageStore.setServicePermissionDraftField('display_name', event.target.value)}
            />
          </label>
          <label className="popup-field">
            <span className="popup-field-label">Description</span>
            <input
              className="text-input popup-input"
              value={manageStore.servicePermissionDraft.description}
              onChange={(event) => manageStore.setServicePermissionDraftField('description', event.target.value)}
            />
          </label>
        </div>
        <div className="popup-actions">
          <button type="button" className="action-btn" onClick={manageStore.closePopup} disabled={manageStore.isLoading}>
            Cancel
          </button>
          <button type="button" className="action-btn action-btn-primary" onClick={manageStore.createServicePermission} disabled={manageStore.isLoading}>
            Declare
          </button>
        </div>
      </div>
    </div>
  )
}

export default observer(ServicePermissionCreate)
