import { createApp } from 'vue'
import { createPinia } from 'pinia'

import App from './app.vue'
import { router } from './router'
import { pushToast } from './libs/toast'
import './style.css'

const app = createApp(App)

app.config.errorHandler = (err, _instance, info) => {
  // eslint-disable-next-line no-console
  console.error('[ShrimpFlow] Vue error:', err, info)
  const message = err instanceof Error ? err.message : String(err)
  pushToast('error', '页面异常', message.slice(0, 160))
}

app.config.warnHandler = (msg, _instance, trace) => {
  // eslint-disable-next-line no-console
  console.warn('[ShrimpFlow] Vue warn:', msg, trace)
}

window.addEventListener('unhandledrejection', e => {
  // eslint-disable-next-line no-console
  console.error('[ShrimpFlow] unhandledrejection', e.reason)
  const message = e.reason instanceof Error ? e.reason.message : String(e.reason)
  pushToast('error', '后台任务出错', message.slice(0, 160))
})

app.use(createPinia())
app.use(router)
app.mount('#app')
