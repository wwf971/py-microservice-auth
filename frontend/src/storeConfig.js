import { makeAutoObservable, runInAction } from 'mobx'

export const configStruct = {
  items: [
    {
      id: 'service_ports',
      label: 'Service Ports',
      type: 'group',
      children: [
        {
          id: 'PORT_SERVICE_GRPC',
          label: 'gRPC Service Port',
          description: 'Port for gRPC authentication service',
          type: 'number',
          defaultValue: 9532,
        },
        {
          id: 'PORT_SERVICE_HTTP',
          label: 'HTTP Service Port',
          description: 'Port for HTTP authentication service',
          type: 'number',
          defaultValue: 9531,
        },
        {
          id: 'PORT_MANAGE',
          label: 'Management Port',
          description: 'Port for management UI',
          type: 'number',
          defaultValue: 9530,
        },
        {
          id: 'PORT_AUX',
          label: 'Auxiliary Port',
          description: 'Port for auxiliary internal API',
          type: 'number',
          defaultValue: 9533,
        },
      ],
    },
    {
      id: 'jwt_config',
      label: 'JWT Configuration',
      type: 'group',
      children: [
        {
          id: 'JWT_ALGORITHM',
          label: 'JWT Algorithm',
          description: 'Algorithm for JWT signing',
          type: 'select',
          options: ['RS256', 'HS256', 'ES256'],
          defaultValue: 'RS256',
        },
        {
          id: 'JWT_EXPIRATION_HOURS',
          label: 'Token Expiration Hours',
          description: 'Long-lived token expiration time in hours',
          type: 'number',
          defaultValue: 24,
        },
      ],
    },
    {
      id: 'security',
      label: 'Security',
      type: 'group',
      children: [
        {
          id: 'BCRYPT_ROUNDS',
          label: 'Bcrypt Rounds',
          description: 'Password hashing rounds',
          type: 'number',
          defaultValue: 12,
        },
      ],
    },
    {
      id: 'db_pool',
      label: 'Database Connection Pool',
      type: 'group',
      children: [
        {
          id: 'DATABASE_POOL_SIZE',
          label: 'Pool Size',
          description: 'Number of maintained connections',
          type: 'number',
          defaultValue: 10,
        },
        {
          id: 'DATABASE_MAX_OVERFLOW',
          label: 'Max Overflow',
          description: 'Maximum overflow connections',
          type: 'number',
          defaultValue: 20,
        },
        {
          id: 'DATABASE_POOL_TIMEOUT',
          label: 'Pool Timeout Seconds',
          description: 'Connection timeout in seconds',
          type: 'number',
          defaultValue: 30,
        },
        {
          id: 'DATABASE_POOL_RECYCLE',
          label: 'Pool Recycle Seconds',
          description: 'Recycle connections after this many seconds',
          type: 'number',
          defaultValue: 3600,
        },
      ],
    },
  ],
}

class ConfigStore {
  config = null
  error = ''
  isLoading = false

  constructor() {
    makeAutoObservable(this, {}, { autoBind: true })
  }

  async fetchConfig() {
    this.isLoading = true
    this.error = ''
    try {
      const response = await fetch('/manage/api/config')
      const result = await response.json()
      runInAction(() => {
        if (result.code === 0) {
          this.config = result.data.config || {}
        } else {
          this.error = result.message || 'Failed to fetch config.'
        }
      })
    } catch (_error) {
      runInAction(() => {
        this.error = 'Error fetching config.'
      })
    } finally {
      runInAction(() => {
        this.isLoading = false
      })
    }
  }

  async updateConfig(id, value) {
    this.isLoading = true
    this.error = ''
    try {
      const response = await fetch('/manage/api/config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ [id]: value }),
      })
      const result = await response.json()
      runInAction(() => {
        if (result.code !== 0) {
          this.error = result.message || 'Config update failed.'
        }
      })
      if (result.code === 0) {
        await this.fetchConfig()
      }
      return result
    } catch (error) {
      const result = { code: -1, message: error.message }
      runInAction(() => {
        this.error = 'Error updating config: ' + error.message
      })
      return result
    } finally {
      runInAction(() => {
        this.isLoading = false
      })
    }
  }

  clear() {
    this.config = null
    this.error = ''
  }
}

export const configStore = new ConfigStore()
