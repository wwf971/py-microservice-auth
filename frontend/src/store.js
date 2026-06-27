import { makeAutoObservable, runInAction } from 'mobx'
import { configStore } from './storeConfig'

class ManageStore {
  username = ''
  password = ''
  token = ''
  message = ''
  messageType = 'success'
  isLoading = false
  isLoggedIn = false
  isPasswordVisible = false
  loginMode = 'credentials'
  loginStatus = ''
  currentUsername = ''
  isPermissionPanelOpening = false

  users = []
  permissions = []
  permissionIncludes = []
  servicePermissions = []
  servicePermissionIncludes = []
  config = null
  selectedToken = null
  tokenSelectedJti = null
  tokenInfoByJti = {}
  tokenColWidthById = {
    jti: 260,
    username: 140,
    token: 520,
    status: 120,
    createdAt: 170,
    expiresAt: 170,
  }
  error = ''
  userSelectedUid = null
  popupCurrent = null
  isUserRowDoubleClickPopupSuppressed = false
  isTokenRowDoubleClickSuppressed = false

  userDraft = {
    username: '',
    password: '',
    permission_codes: [],
    service_permissions: [],
  }

  servicePermissionDraft = {
    service_id: '',
    permission_code: '',
    display_name: '',
    description: '',
  }

  permissionDraft = {
    uid: null,
    permission_codes: [],
    service_permissions: [],
  }

  serverStatusByKey = {
    aux: { name: 'aux', port: 9533, isAlive: null, lastChecked: null, isChecking: false },
    grpc: { name: 'grpc', port: 9532, isAlive: null, lastChecked: null, isChecking: false },
    http: { name: 'http', port: 9531, isAlive: null, lastChecked: null, isChecking: false },
  }

  dbs = []
  dbCurrentId = 0
  dbSelectedId = null
  dbStatusMessageById = {}
  dbError = ''

  constructor() {
    makeAutoObservable(this, {}, { autoBind: true })
    this.init()
  }

  init() {
    if (typeof window === 'undefined' || !window.localStorage) return
    const tokenSaved = window.localStorage.getItem('authToken')
    if (!tokenSaved) return
    this.token = tokenSaved
    this.loginMode = 'token'
    this.currentUsername = window.localStorage.getItem('authUsername') || ''
  }

  async onDataChangeRequest(type, params = {}) {
    if (type === 'set-username') {
      this.username = params.username || ''
      return { code: 0 }
    }
    if (type === 'set-password') {
      this.password = params.password || ''
      return { code: 0 }
    }
    if (type === 'set-token') {
      this.token = params.token || ''
      return { code: 0 }
    }
    if (type === 'set-login-mode') {
      this.loginMode = params.loginMode === 'token' ? 'token' : 'credentials'
      this.message = ''
      return { code: 0 }
    }
    if (type === 'toggle-password-visible') {
      this.isPasswordVisible = !this.isPasswordVisible
      return { code: 0 }
    }
    if (type === 'submit-credentials') {
      await this.loginWithCredentials()
      return { code: 0 }
    }
    if (type === 'submit-token') {
      await this.loginWithToken()
      return { code: 0 }
    }
    return { code: 0 }
  }

  async loginWithCredentials() {
    this.isLoading = true
    this.message = ''
    try {
      const response = await fetch('/manage/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username: this.username, password: this.password }),
      })
      const result = await response.json()
      runInAction(() => {
        if (result.code === 0) {
          this.token = result?.data?.token || ''
          this.currentUsername = result?.data?.username || this.username
          this.isLoggedIn = true
          this.loginStatus = 'Authenticated'
          this.messageType = 'success'
          this.message = 'Login successful.'
          if (typeof window !== 'undefined' && window.localStorage && this.token) {
            window.localStorage.setItem('authToken', this.token)
            window.localStorage.setItem('authUsername', this.currentUsername)
          }
        } else {
          this.messageType = 'error'
          this.message = result.message || 'Login failed.'
        }
      })
    } catch (_error) {
      runInAction(() => {
        this.messageType = 'error'
        this.message = 'Login request failed.'
      })
    } finally {
      runInAction(() => {
        this.isLoading = false
      })
    }
  }

  async loginWithToken() {
    if (!this.token) {
      this.messageType = 'error'
      this.message = 'Token is required.'
      return
    }
    this.isLoading = true
    this.message = ''
    try {
      const response = await fetch('/manage/api/current_user', {
        headers: this.authHeaders,
      })
      const result = await response.json()
      runInAction(() => {
        if (result.code === 0) {
          this.currentUsername = result?.data?.user?.username || ''
          this.isLoggedIn = true
          this.loginStatus = 'Authenticated'
          this.messageType = 'success'
          this.message = 'Token login successful.'
          if (typeof window !== 'undefined' && window.localStorage) {
            window.localStorage.setItem('authToken', this.token)
            if (this.currentUsername) {
              window.localStorage.setItem('authUsername', this.currentUsername)
            }
          }
        } else {
          this.messageType = 'error'
          this.message = result.message || 'Token login failed.'
        }
      })
    } catch (_error) {
      runInAction(() => {
        this.messageType = 'error'
        this.message = 'Token login request failed.'
      })
    } finally {
      runInAction(() => {
        this.isLoading = false
      })
    }
  }

  logout() {
    this.isLoggedIn = false
    this.token = ''
    this.password = ''
    this.loginStatus = ''
    this.currentUsername = ''
    this.users = []
    this.config = null
    configStore.clear()
    this.selectedToken = null
    this.tokenSelectedJti = null
    this.tokenInfoByJti = {}
    this.userSelectedUid = null
    this.popupCurrent = null
    if (typeof window !== 'undefined' && window.localStorage) {
      window.localStorage.removeItem('authToken')
      window.localStorage.removeItem('authUsername')
    }
  }

  async bootstrap() {
    await Promise.all([
      this.fetchPermissions(),
      this.fetchUsers(),
      configStore.fetchConfig(),
      this.fetchDbs(),
      this.checkAllServers(),
    ])
  }

  flush() {
    this.users = []
    this.permissions = []
    this.permissionIncludes = []
    this.servicePermissions = []
    this.servicePermissionIncludes = []
    this.config = null
    configStore.clear()
    this.selectedToken = null
    this.userSelectedUid = null
    this.popupCurrent = null
    this.error = ''
    this.dbError = ''
    this.dbStatusMessageById = {}
  }

  get userSelected() {
    return this.users.find((user) => user.uid === this.userSelectedUid) || null
  }

  get userRows() {
    return this.usersSortedForDisplay.map((user) => ({
      id: String(user.uid),
      data: {
        uid: user.uid,
        username: {
          text: user.username,
          isCurrentUser: this.isCurrentUser(user),
        },
        passwordHash: user.password_hash,
        tokenCount: user.jwt_token_ids?.length || 0,
        permissions: this.getUserPermissionText(user),
      },
    }))
  }

  get usersSortedForDisplay() {
    if (!this.currentUsername) return this.users
    return [...this.users].sort((userA, userB) => {
      const isCurrentA = this.isCurrentUser(userA)
      const isCurrentB = this.isCurrentUser(userB)
      if (isCurrentA && !isCurrentB) return -1
      if (!isCurrentA && isCurrentB) return 1
      return 0
    })
  }

  get userFolderData() {
    return {
      columns: {
        uid: { data: 'UID', align: 'left' },
        username: { data: 'Username', align: 'left' },
        tokenCount: { data: 'JWT Tokens', align: 'left' },
        permissions: { data: 'Permissions', align: 'left' },
      },
      colsOrder: ['uid', 'username', 'tokenCount', 'permissions'],
      rows: this.userRows,
      rowIdsSelected: this.userSelectedUid ? [String(this.userSelectedUid)] : [],
      contextMenuItems: [
        { id: 'view_tokens', label: 'View Tokens' },
        { id: 'issue_token', label: 'Issue Token' },
        { id: 'edit_permission', label: 'Edit Permission' },
        { id: 'delete_user', label: 'Delete' },
      ],
      statusBar: {
        itemCount: this.users.length,
        messageState: this.error ? { status: 'error', messageText: this.error } : null,
      },
    }
  }

  get userFolderConfig() {
    return {
      colSizeById: {
        uid: { width: 90, minWidth: 70, resizable: true },
        username: { width: 180, minWidth: 130, resizable: true },
        tokenCount: { width: 100, minWidth: 80, resizable: true },
        permissions: { width: 520, minWidth: 220, resizable: true },
      },
      selectionMode: 'single',
      isListOnly: true,
      isLocked: this.isUserFolderLocked,
      bodyHeight: 280,
      isStatusBarVisible: true,
    }
  }

  get tokenRows() {
    return this.users.flatMap((user) => (
      (user.jwt_token_ids || []).map((jti) => {
        const tokenInfo = this.tokenInfoByJti[jti] || {}
        const createdAt = tokenInfo.created_at || ''
        const expiresAt = tokenInfo.expires_at || ''
        return {
          id: jti,
          data: {
            jti,
            uid: user.uid,
            username: user.username,
            token: tokenInfo.token || '',
            status: formatTokenStatus(tokenInfo.status_code),
            createdAt: {
              text: formatUnixTimestamp(createdAt, tokenInfo.created_at_timezone),
              title: createdAt ? String(createdAt) : '',
            },
            expiresAt: {
              text: formatUnixTimestamp(expiresAt, tokenInfo.created_at_timezone),
              title: expiresAt ? String(expiresAt) : '',
            },
          },
        }
      })
    ))
  }

  get tokenFolderData() {
    return {
      columns: {
        jti: { data: 'JTI', align: 'left' },
        username: { data: 'Username', align: 'left' },
        token: { data: 'Raw Token', align: 'left' },
        status: { data: 'Status', align: 'left' },
        createdAt: { data: 'Created At', align: 'left' },
        expiresAt: { data: 'Expires At', align: 'left' },
      },
      colsOrder: ['jti', 'username', 'token', 'status', 'createdAt', 'expiresAt'],
      rows: this.tokenRows,
      rowIdsSelected: this.tokenSelectedJti ? [this.tokenSelectedJti] : [],
      contextMenuItems: [
        { id: 'view_token', label: 'View Token' },
        { id: 'view_user', label: 'View User' },
        { id: 'revoke_token', label: 'Revoke Token' },
        { id: 'delete_token', label: 'Delete' },
      ],
      statusBar: {
        itemCount: this.tokenRows.length,
        messageState: this.error ? { status: 'error', messageText: this.error } : null,
      },
    }
  }

  get tokenFolderConfig() {
    return {
      colSizeById: {
        jti: { width: 260, minWidth: 140, resizable: true },
        username: { width: 140, minWidth: 90, resizable: true },
        token: { width: 520, minWidth: 180, resizable: true },
        status: { width: 120, minWidth: 80, resizable: true },
        createdAt: { width: 170, minWidth: 120, resizable: true },
        expiresAt: { width: 170, minWidth: 120, resizable: true },
      },
      selectionMode: 'single',
      isListOnly: true,
      isLocked: this.isLoading,
      bodyHeight: 280,
      isStatusBarVisible: true,
      colWidthById: this.tokenColWidthById,
    }
  }

  get isTokenActionDisabled() {
    return this.isLoading || !this.tokenSelectedJti
  }

  get tokenSelectedRow() {
    return this.tokenRows.find((row) => row.id === this.tokenSelectedJti) || null
  }

  get uidForTokenIssue() {
    return this.userSelected?.uid || this.tokenSelectedRow?.data?.uid || null
  }

  get isUserActionDisabled() {
    return this.isUserFolderLocked || !this.userSelected
  }

  get isUserFolderLocked() {
    return this.isLoading || this.isPermissionPanelOpening
  }

  isCurrentUser(user) {
    return Boolean(this.currentUsername && user?.username === this.currentUsername)
  }

  getUserPermissionText(user) {
    const permissionParts = (user.permission_codes || []).map((permissionCode) => this.permissionDisplay(permissionCode))
    const serviceParts = (user.service_permissions || []).map((item) => this.servicePermissionDisplay(item))
    const parts = [...permissionParts, ...serviceParts]
    return parts.length ? parts.join(', ') : 'none'
  }

  openPopup(popupCurrent) {
    this.popupCurrent = popupCurrent
    if (popupCurrent === 'user-create') {
      this.userDraft = { username: '', password: '', permission_codes: [], service_permissions: [] }
    }
    if (popupCurrent === 'permission-edit') {
      this.isPermissionPanelOpening = true
      this.startPermissionEdit()
      if (!this.userSelected) {
        this.isPermissionPanelOpening = false
      }
    }
    if (popupCurrent === 'service-permission-create') {
      this.servicePermissionDraft = {
        service_id: '',
        permission_code: '',
        display_name: '',
        description: '',
      }
    }
  }

  closePopup() {
    this.popupCurrent = null
    this.isPermissionPanelOpening = false
  }

  markPermissionPanelReady() {
    this.isPermissionPanelOpening = false
  }

  selectUser(uid) {
    this.userSelectedUid = uid
  }

  selectUserFromTokenRow(jti) {
    const row = this.tokenRows.find((item) => item.id === jti)
    if (row?.data?.uid != null) {
      this.userSelectedUid = row.data.uid
    }
  }

  handleUserFolderEvent(eventType, eventData = {}) {
    if (this.isUserFolderLocked) {
      return { code: 0 }
    }
    if (eventType === 'rowIdsSelectedChange') {
      const rowId = eventData.rowIdsSelected?.[0]
      this.userSelectedUid = rowId ? Number(rowId) : null
    }
    if (eventType === 'rowClick') {
      this.userSelectedUid = Number(eventData.rowId)
    }
    if (eventType === 'rowInteraction' && eventData.type === 'double-click') {
      if (isUserTokenCountColumnDoubleClick(eventData.nativeEvent)) {
        this.userSelectedUid = Number(eventData.rowId)
        this.isUserRowDoubleClickPopupSuppressed = true
        return { code: 0, intent: 'viewUserTokens' }
      }
    }
    if (eventType === 'rowDoubleClick') {
      this.userSelectedUid = Number(eventData.rowId)
      window.setTimeout(() => {
        runInAction(() => {
          if (this.isUserRowDoubleClickPopupSuppressed) {
            this.isUserRowDoubleClickPopupSuppressed = false
            return
          }
          this.openPopup('permission-edit')
        })
      }, 0)
    }
    if (eventType === 'userTokenCountDoubleClick') {
      this.userSelectedUid = Number(eventData.rowId)
      this.isUserRowDoubleClickPopupSuppressed = true
      return { code: 0, intent: 'viewUserTokens' }
    }
    if (eventType === 'rowContextMenuItemClick') {
      const uid = Number(eventData.rowId)
      this.userSelectedUid = uid
      const itemId = eventData.item?.id
      if (itemId === 'issue_token') {
        this.issueToken(uid)
      }
      if (itemId === 'edit_permission') {
        this.openPopup('permission-edit')
      }
      if (itemId === 'delete_user') {
        this.deleteUser(uid)
      }
    }
    return { code: 0 }
  }

  handleTokenFolderEvent(eventType, eventData = {}) {
    if (eventType === 'colResize' && eventData.colWidthByIdNext) {
      this.tokenColWidthById = eventData.colWidthByIdNext
      return { code: 0 }
    }
    if (eventType === 'rowIdsSelectedChange') {
      this.tokenSelectedJti = eventData.rowIdsSelected?.[0] || null
    }
    if (eventType === 'rowClick') {
      this.tokenSelectedJti = eventData.rowId
    }
    if (eventType === 'rowDoubleClick') {
      this.tokenSelectedJti = eventData.rowId
      window.setTimeout(() => {
        runInAction(() => {
          if (this.isTokenRowDoubleClickSuppressed) {
            this.isTokenRowDoubleClickSuppressed = false
            return
          }
          this.viewToken(eventData.rowId)
        })
      }, 0)
    }
    if (eventType === 'tokenUsernameDoubleClick') {
      this.tokenSelectedJti = eventData.rowId
      this.selectUserFromTokenRow(eventData.rowId)
      this.isTokenRowDoubleClickSuppressed = true
    }
    if (eventType === 'rowContextMenuItemClick') {
      this.tokenSelectedJti = eventData.rowId
      const itemId = eventData.item?.id
      if (itemId === 'view_token') {
        this.viewToken(eventData.rowId)
      }
      if (itemId === 'view_user') {
        this.selectUserFromTokenRow(eventData.rowId)
      }
      if (itemId === 'revoke_token') {
        this.revokeToken(eventData.rowId)
      }
      if (itemId === 'delete_token') {
        this.deleteToken(eventData.rowId)
      }
    }
    return { code: 0 }
  }

  async fetchUsers() {
    this.isLoading = true
    this.error = ''
    try {
      const response = await fetch('/manage/api/users', {
        headers: this.authHeaders,
      })
      const result = await response.json()
      let usersNext = []
      runInAction(() => {
        if (result.code === 0) {
          usersNext = result.data.users || []
          this.users = usersNext
          const tokenIdSet = new Set(usersNext.flatMap((user) => user.jwt_token_ids || []))
          for (const jti of Object.keys(this.tokenInfoByJti)) {
            if (!tokenIdSet.has(jti)) {
              delete this.tokenInfoByJti[jti]
            }
          }
          if (this.tokenSelectedJti && !tokenIdSet.has(this.tokenSelectedJti)) {
            this.tokenSelectedJti = null
          }
        } else {
          this.error = result.message || 'Failed to fetch users.'
        }
      })
      if (result.code === 0) {
        await this.fetchTokenInfoForUsers(usersNext)
      }
    } catch (error) {
      runInAction(() => {
        this.error = 'Error fetching users: ' + error.message
      })
    } finally {
      runInAction(() => {
        this.isLoading = false
      })
    }
  }

  setUserDraftField(key, value) {
    this.userDraft[key] = value
  }

  setServicePermissionDraftField(key, value) {
    this.servicePermissionDraft[key] = value
  }

  get authHeaders() {
    return {
      Authorization: `Bearer ${this.token}`,
      'X-Auth-Token': this.token,
    }
  }

  get permissionIncludeByCode() {
    const includeByCode = {}
    for (const item of this.permissionIncludes) {
      if (!includeByCode[item.permission_code]) includeByCode[item.permission_code] = []
      includeByCode[item.permission_code].push(item.permission_code_included)
    }
    return includeByCode
  }

  get servicePermissionIncludeByKey() {
    const includeByKey = {}
    for (const item of this.servicePermissionIncludes) {
      const key = `${item.service_id}::${item.permission_code}`
      if (!includeByKey[key]) includeByKey[key] = []
      includeByKey[key].push(item.permission_code_included)
    }
    return includeByKey
  }

  permissionDisplay(permissionCode) {
    const item = this.permissions.find((permission) => permission.permission_code === permissionCode)
    return item ? `${item.display_name} (${permissionCode})` : String(permissionCode)
  }

  servicePermissionDisplay(item) {
    const meta = this.servicePermissions.find((permission) => (
      permission.service_id === item.service_id && permission.permission_code === item.permission_code
    ))
    if (!meta) return `${item.service_id}::${item.permission_code}`
    return `${meta.service_id}::${meta.permission_code} ${meta.display_name}`
  }

  isUserPermissionAssigned(user, permissionCode) {
    return (user.permission_codes || []).includes(permissionCode)
  }

  isUserServicePermissionAssigned(user, servicePermission) {
    return (user.service_permissions || []).some((item) => (
      item.service_id === servicePermission.service_id && item.permission_code === servicePermission.permission_code
    ))
  }

  startPermissionEdit() {
    const user = this.userSelected
    if (!user) return
    this.permissionDraft = {
      uid: user.uid,
      permission_codes: [...(user.permission_codes || [])],
      service_permissions: (user.service_permissions || []).map((item) => ({
        service_id: item.service_id,
        permission_code: item.permission_code,
      })),
    }
  }

  isPermissionDraftAssigned(permissionCode) {
    return (this.permissionDraft.permission_codes || []).includes(permissionCode)
  }

  isServicePermissionDraftAssigned(servicePermission) {
    return (this.permissionDraft.service_permissions || []).some((item) => (
      item.service_id === servicePermission.service_id && item.permission_code === servicePermission.permission_code
    ))
  }

  togglePermissionDraft(permissionCode) {
    const permissionCodes = new Set(this.permissionDraft.permission_codes || [])
    if (permissionCodes.has(permissionCode)) {
      permissionCodes.delete(permissionCode)
    } else {
      permissionCodes.add(permissionCode)
    }
    this.permissionDraft.permission_codes = Array.from(permissionCodes)
  }

  toggleServicePermissionDraft(servicePermission) {
    const servicePermissions = [...(this.permissionDraft.service_permissions || [])]
    const itemIndex = servicePermissions.findIndex((item) => (
      item.service_id === servicePermission.service_id && item.permission_code === servicePermission.permission_code
    ))
    if (itemIndex >= 0) {
      servicePermissions.splice(itemIndex, 1)
    } else {
      servicePermissions.push({
        service_id: servicePermission.service_id,
        permission_code: servicePermission.permission_code,
      })
    }
    this.permissionDraft.service_permissions = servicePermissions
  }

  async savePermissionDraft() {
    if (!this.permissionDraft.uid) {
      this.error = 'Select a user first.'
      return
    }
    await this.updateUserPermissions(
      this.permissionDraft.uid,
      this.permissionDraft.permission_codes,
      this.permissionDraft.service_permissions,
    )
    if (!this.error) {
      this.closePopup()
    }
  }

  async fetchPermissions() {
    try {
      const response = await fetch('/manage/api/permissions', {
        headers: this.authHeaders,
      })
      const result = await response.json()
      runInAction(() => {
        if (result.code === 0) {
          this.permissions = result.data.permissions || []
          this.permissionIncludes = result.data.permission_includes || []
          this.servicePermissions = result.data.service_permissions || []
          this.servicePermissionIncludes = result.data.service_permission_includes || []
        } else {
          this.error = result.message || 'Failed to fetch permissions.'
        }
      })
    } catch (error) {
      runInAction(() => {
        this.error = 'Error fetching permissions: ' + error.message
      })
    }
  }

  async updateUserPermissions(uid, permissionCodes, servicePermissions) {
    this.isLoading = true
    this.error = ''
    try {
      const response = await fetch(`/manage/api/users/${uid}/permissions`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          ...this.authHeaders,
        },
        body: JSON.stringify({
          permission_codes: permissionCodes,
          service_permissions: servicePermissions,
        }),
      })
      const result = await response.json()
      runInAction(() => {
        if (result.code !== 0) {
          this.error = result.message || 'Failed to update permissions.'
        }
      })
      if (result.code === 0) {
        await this.fetchUsers()
      }
    } catch (error) {
      runInAction(() => {
        this.error = 'Error updating permissions: ' + error.message
      })
    } finally {
      runInAction(() => {
        this.isLoading = false
      })
    }
  }

  async toggleUserPermission(user, permissionCode) {
    const permissionCodes = new Set(user.permission_codes || [])
    if (permissionCodes.has(permissionCode)) {
      permissionCodes.delete(permissionCode)
    } else {
      permissionCodes.add(permissionCode)
    }
    await this.updateUserPermissions(user.uid, Array.from(permissionCodes), user.service_permissions || [])
  }

  async toggleUserServicePermission(user, servicePermission) {
    const servicePermissions = [...(user.service_permissions || [])]
    const itemIndex = servicePermissions.findIndex((item) => (
      item.service_id === servicePermission.service_id && item.permission_code === servicePermission.permission_code
    ))
    if (itemIndex >= 0) {
      servicePermissions.splice(itemIndex, 1)
    } else {
      servicePermissions.push({
        service_id: servicePermission.service_id,
        permission_code: servicePermission.permission_code,
      })
    }
    await this.updateUserPermissions(user.uid, user.permission_codes || [], servicePermissions)
  }

  async createServicePermission() {
    const permissionCode = Number(this.servicePermissionDraft.permission_code)
    if (!this.servicePermissionDraft.service_id || !permissionCode) {
      this.error = 'Service id and permission code are required.'
      return
    }

    this.isLoading = true
    this.error = ''
    try {
      const response = await fetch('/manage/api/service_permissions', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...this.authHeaders,
        },
        body: JSON.stringify({
          service_id: this.servicePermissionDraft.service_id,
          permission_code: permissionCode,
          display_name: this.servicePermissionDraft.display_name,
          description: this.servicePermissionDraft.description,
          permission_codes_included: [],
        }),
      })
      const result = await response.json()
      runInAction(() => {
        if (result.code === 0) {
          this.servicePermissionDraft = {
            service_id: '',
            permission_code: '',
            display_name: '',
            description: '',
          }
        } else {
          this.error = result.message || 'Failed to declare service permission.'
        }
      })
      if (result.code === 0) {
        await this.fetchPermissions()
        this.closePopup()
      }
    } catch (error) {
      runInAction(() => {
        this.error = 'Error declaring service permission: ' + error.message
      })
    } finally {
      runInAction(() => {
        this.isLoading = false
      })
    }
  }

  async createUser() {
    if (!this.userDraft.username || !this.userDraft.password) {
      this.error = 'Username and password are required.'
      return
    }
    this.isLoading = true
    this.error = ''
    try {
      const response = await fetch('/manage/api/users', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...this.authHeaders },
        body: JSON.stringify(this.userDraft),
      })
      const result = await response.json()
      runInAction(() => {
        if (result.code === 0) {
          this.userDraft = { username: '', password: '', permission_codes: [], service_permissions: [] }
        } else {
          this.error = result.message || 'Failed to create user.'
        }
      })
      if (result.code === 0) {
        await this.fetchUsers()
        this.closePopup()
      }
    } catch (error) {
      runInAction(() => {
        this.error = 'Error creating user: ' + error.message
      })
    } finally {
      runInAction(() => {
        this.isLoading = false
      })
    }
  }

  async deleteUser(uid) {
    this.isLoading = true
    this.error = ''
    try {
      const response = await fetch(`/manage/api/users/${uid}`, {
        method: 'DELETE',
        headers: this.authHeaders,
      })
      const result = await response.json()
      runInAction(() => {
        if (result.code !== 0) {
          this.error = result.message || 'Failed to delete user.'
        }
      })
      if (result.code === 0) {
        await this.fetchUsers()
      }
    } catch (error) {
      runInAction(() => {
        this.error = 'Error deleting user: ' + error.message
      })
    } finally {
      runInAction(() => {
        this.isLoading = false
      })
    }
  }

  async issueToken(uid) {
    this.isLoading = true
    this.error = ''
    try {
      const response = await fetch('/manage/api/tokens/issue', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...this.authHeaders },
        body: JSON.stringify({ uid }),
      })
      const result = await response.json()
      runInAction(() => {
        if (result.code !== 0) {
          this.error = result.message || 'Failed to issue token.'
        }
      })
      if (result.code === 0) {
        await this.fetchUsers()
        if (result.data?.jti) {
          this.tokenSelectedJti = result.data.jti
          await this.viewToken(result.data.jti)
        }
      }
    } catch (error) {
      runInAction(() => {
        this.error = 'Error issuing token: ' + error.message
      })
    } finally {
      runInAction(() => {
        this.isLoading = false
      })
    }
  }

  async viewToken(jti) {
    this.isLoading = true
    this.error = ''
    try {
      const response = await fetch(`/manage/api/tokens/${jti}`, {
        headers: this.authHeaders,
      })
      const result = await response.json()
      runInAction(() => {
        if (result.code === 0) {
          this.selectedToken = result.data
          this.tokenSelectedJti = jti
          this.tokenInfoByJti[jti] = result.data
        } else {
          this.error = result.message || 'Failed to fetch token.'
        }
      })
    } catch (error) {
      runInAction(() => {
        this.error = 'Error fetching token: ' + error.message
      })
    } finally {
      runInAction(() => {
        this.isLoading = false
      })
    }
  }

  async fetchTokenInfoForUsers(users) {
    const tokenIds = users.flatMap((user) => user.jwt_token_ids || [])
    await Promise.all(tokenIds.map((jti) => this.fetchTokenInfoIfNeeded(jti)))
  }

  async fetchTokenInfoIfNeeded(jti) {
    if (!jti || this.tokenInfoByJti[jti]) return
    try {
      const response = await fetch(`/manage/api/tokens/${jti}`, {
        headers: this.authHeaders,
      })
      const result = await response.json()
      runInAction(() => {
        if (result.code === 0) {
          this.tokenInfoByJti[jti] = result.data
        }
      })
    } catch (_error) {}
  }

  async deleteToken(jti) {
    if (!jti) return
    this.isLoading = true
    this.error = ''
    try {
      const response = await fetch(`/manage/api/tokens/${jti}`, {
        method: 'DELETE',
        headers: this.authHeaders,
      })
      const result = await response.json()
      runInAction(() => {
        if (result.code === 0) {
          delete this.tokenInfoByJti[jti]
          if (this.tokenSelectedJti === jti) this.tokenSelectedJti = null
          if (this.selectedToken?.jti === jti) this.selectedToken = null
        } else {
          this.error = result.message || 'Failed to delete token.'
        }
      })
      if (result.code === 0) {
        await this.fetchUsers()
      }
    } catch (error) {
      runInAction(() => {
        this.error = 'Error deleting token: ' + error.message
      })
    } finally {
      runInAction(() => {
        this.isLoading = false
      })
    }
  }

  async revokeToken(jti) {
    if (!jti) return
    this.isLoading = true
    this.error = ''
    try {
      const response = await fetch(`/manage/api/tokens/${jti}/revoke`, {
        method: 'POST',
        headers: this.authHeaders,
      })
      const result = await response.json()
      runInAction(() => {
        if (result.code !== 0) {
          this.error = result.message || 'Failed to revoke token.'
        }
      })
      if (result.code === 0) {
        delete this.tokenInfoByJti[jti]
        await this.fetchUsers()
        await this.fetchTokenInfoIfNeeded(jti)
      }
    } catch (error) {
      runInAction(() => {
        this.error = 'Error revoking token: ' + error.message
      })
    } finally {
      runInAction(() => {
        this.isLoading = false
      })
    }
  }

  async checkExpiredTokens() {
    this.isLoading = true
    this.error = ''
    try {
      const response = await fetch('/manage/api/tokens/expired/check', {
        method: 'POST',
        headers: this.authHeaders,
      })
      const result = await response.json()
      runInAction(() => {
        if (result.code !== 0) {
          this.error = result.message || 'Failed to check expired tokens.'
        } else {
          const count = Number(result.data?.expired_count || 0)
          this.error = count > 0 ? `Expired tokens found: ${count}` : 'No valid tokens are expired.'
        }
      })
      if (result.code === 0) {
        await this.fetchUsers()
      }
    } catch (error) {
      runInAction(() => {
        this.error = 'Error checking expired tokens: ' + error.message
      })
    } finally {
      runInAction(() => {
        this.isLoading = false
      })
    }
  }

  async removeTokensByStatus(statusMode) {
    this.isLoading = true
    this.error = ''
    try {
      const response = await fetch('/manage/api/tokens/remove', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...this.authHeaders },
        body: JSON.stringify({ statusMode }),
      })
      const result = await response.json()
      runInAction(() => {
        if (result.code !== 0) {
          this.error = result.message || 'Failed to remove tokens.'
        } else {
          this.error = `Removed tokens: ${Number(result.data?.deleted_count || 0)}`
        }
      })
      if (result.code === 0) {
        await this.fetchUsers()
      }
    } catch (error) {
      runInAction(() => {
        this.error = 'Error removing tokens: ' + error.message
      })
    } finally {
      runInAction(() => {
        this.isLoading = false
      })
    }
  }

  async checkServer(serverKey) {
    const server = this.serverStatusByKey[serverKey]
    if (!server || server.isChecking) return
    const timeStarted = Date.now()
    runInAction(() => {
      server.isChecking = true
    })
    try {
      const response = await fetch(`/manage/api/server_status/${server.name}`)
      const result = await response.json()
      await waitUntilMinimumElapsed(timeStarted, 200)
      runInAction(() => {
        server.isAlive = result.code === 0 ? result.data.is_alive : false
        server.port = result.code === 0 ? result.data.port : server.port
        server.lastChecked = new Date().toISOString()
        server.isChecking = false
      })
    } catch (_error) {
      await waitUntilMinimumElapsed(timeStarted, 200)
      runInAction(() => {
        server.isAlive = false
        server.lastChecked = new Date().toISOString()
        server.isChecking = false
      })
    }
  }

  async checkAllServers() {
    await Promise.all(Object.keys(this.serverStatusByKey).map((serverKey) => this.checkServer(serverKey)))
  }

  async fetchDbs() {
    const timeStarted = Date.now()
    this.isLoading = true
    this.dbError = ''
    try {
      const response = await fetch('/manage/api/databases')
      const result = await response.json()
      await waitUntilMinimumElapsed(timeStarted, 200)
      runInAction(() => {
        if (result.code === 0) {
          this.dbs = result.data.databases || []
          this.dbCurrentId = result.data.current_database_id
        } else {
          this.dbError = result.message || 'Failed to fetch dbs.'
        }
      })
    } catch (error) {
      await waitUntilMinimumElapsed(timeStarted, 200)
      runInAction(() => {
        this.dbError = 'Error fetching dbs: ' + error.message
      })
    } finally {
      runInAction(() => {
        this.isLoading = false
      })
    }
  }

  get dbSelected() {
    return this.dbs.find((db) => db.id === this.dbSelectedId) || null
  }

  selectDb(dbId) {
    this.dbSelectedId = dbId
  }

  setDbStatusMessage(dbId, statusMessage) {
    if (!statusMessage) {
      delete this.dbStatusMessageById[dbId]
      return
    }
    this.dbStatusMessageById[dbId] = statusMessage
  }

  dismissDbStatusMessage(dbId) {
    delete this.dbStatusMessageById[dbId]
  }

  async testDb(dbId) {
    const timeStarted = Date.now()
    try {
      const response = await fetch(`/manage/api/databases/${dbId}/test`, { method: 'POST' })
      const result = await response.json()
      await waitUntilMinimumElapsed(timeStarted, 200)
      runInAction(() => {
        if (result.code === 0) {
          this.setDbStatusMessage(dbId, {
            status: 'success',
            messageText: result.message || 'connection ok',
          })
        } else {
          this.setDbStatusMessage(dbId, {
            status: 'error',
            messageText: result.message || 'connection failed',
          })
        }
      })
      return result
    } catch (error) {
      await waitUntilMinimumElapsed(timeStarted, 200)
      runInAction(() => {
        this.setDbStatusMessage(dbId, {
          status: 'error',
          messageText: 'connection test failed: ' + error.message,
        })
      })
      return { code: -1, message: error.message }
    }
  }

  async removeDb(dbId) {
    this.isLoading = true
    this.dbError = ''
    try {
      const response = await fetch(`/manage/api/databases/${dbId}`, { method: 'DELETE' })
      const result = await response.json()
      runInAction(() => {
        if (result.code === 0) {
          this.dbSelectedId = null
        } else {
          this.dbError = result.message || 'Failed to remove db.'
        }
      })
      if (result.code === 0) {
        await this.fetchDbs()
      }
    } catch (error) {
      runInAction(() => {
        this.dbError = 'Error removing db: ' + error.message
      })
    } finally {
      runInAction(() => {
        this.isLoading = false
      })
    }
  }

  async switchDb(dbId) {
    this.isLoading = true
    this.dbError = ''
    try {
      const response = await fetch(`/manage/api/databases/switch/${dbId}`, { method: 'POST' })
      const result = await response.json()
      runInAction(() => {
        if (result.code !== 0) {
          this.dbError = result.message || 'Failed to switch db.'
        }
      })
      if (result.code === 0) {
        this.flush()
        await this.bootstrap()
      }
    } catch (error) {
      runInAction(() => {
        this.dbError = 'Error switching db: ' + error.message
      })
    } finally {
      runInAction(() => {
        this.isLoading = false
      })
    }
  }

}

const USER_FOLDER_TOKEN_COUNT_COL_INDEX = 2

function isUserTokenCountColumnDoubleClick(nativeEvent) {
  const target = nativeEvent?.target
  if (!target?.closest) return false
  if (target.closest('[data-user-token-count-cell]')) return true
  const cellEl = target.closest('.folder-body-cell')
  const rowEl = target.closest('[data-row-id]')
  if (!cellEl || !rowEl) return false
  const cells = rowEl.querySelectorAll('.folder-body-cell')
  return cells[USER_FOLDER_TOKEN_COUNT_COL_INDEX] === cellEl
}

function formatTokenStatus(statusCode) {
  if (statusCode === 1) return 'valid'
  if (statusCode === -1) return 'expired'
  if (statusCode === -2) return 'revoked'
  if (statusCode === -3) return 'retained'
  return statusCode ? String(statusCode) : ''
}

function formatUnixTimestamp(timestamp, timezoneHour) {
  if (!timestamp) return ''
  const timestampNumber = Number(timestamp)
  if (!Number.isFinite(timestampNumber)) return ''
  const timezoneHourNumber = Number.isFinite(Number(timezoneHour))
    ? Number(timezoneHour)
    : -new Date().getTimezoneOffset() / 60
  const date = new Date((timestampNumber + timezoneHourNumber * 3600) * 1000)
  const year = date.getUTCFullYear()
  const month = pad2(date.getUTCMonth() + 1)
  const day = pad2(date.getUTCDate())
  const hour = pad2(date.getUTCHours())
  const minute = pad2(date.getUTCMinutes())
  const second = pad2(date.getUTCSeconds())
  const centisecond = pad2(Math.floor(date.getUTCMilliseconds() / 10))
  const timezoneSign = timezoneHourNumber >= 0 ? '+' : '-'
  return `${year}${month}${day}_${hour}${minute}${second}${centisecond}${timezoneSign}${pad2(Math.abs(Math.trunc(timezoneHourNumber)))}`
}

function pad2(value) {
  return String(value).padStart(2, '0')
}

function waitUntilMinimumElapsed(timeStarted, durationMs) {
  const delayMs = Math.max(0, durationMs - (Date.now() - timeStarted))
  if (delayMs <= 0) return Promise.resolve()
  return new Promise((resolve) => {
    window.setTimeout(resolve, delayMs)
  })
}

export const manageStore = new ManageStore()

