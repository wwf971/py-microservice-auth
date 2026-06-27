import { observer } from 'mobx-react-lite'
import { ConfigPanel, TabsOnTop } from '@wwf971/react-comp-misc'
import { configStore, configStruct } from './storeConfig'

function ConfigManagePanel() {
  return (
    <div className="config-panel">
      <div className="config-section-title">Configuration</div>
      <TabsOnTop defaultTab="Edit Config">
        <TabsOnTop.Tab label="Edit Config">
          {configStore.config ? (
            <ConfigPanel
              configStruct={configStruct}
              configValue={configStore.config}
              onChangeAttempt={configStore.updateConfig}
              missingItemStrategy="setDefault"
            />
          ) : (
            <div className="loading-text">{configStore.isLoading ? 'Loading configuration...' : 'Configuration not loaded.'}</div>
          )}
        </TabsOnTop.Tab>

        <TabsOnTop.Tab label="Raw JSON">
          {configStore.config ? (
            <pre className="config-json">{JSON.stringify(configStore.config, null, 2)}</pre>
          ) : (
            <div className="loading-text">{configStore.isLoading ? 'Loading configuration...' : 'Configuration not loaded.'}</div>
          )}
        </TabsOnTop.Tab>
      </TabsOnTop>
      {configStore.error && <div className="error-message">{configStore.error}</div>}
    </div>
  )
}

export default observer(ConfigManagePanel)
