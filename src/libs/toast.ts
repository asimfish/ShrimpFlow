import { reactive, readonly } from 'vue'

export type ToastLevel = 'info' | 'success' | 'warn' | 'error'

export type ToastEntry = {
  id: number
  level: ToastLevel
  title: string
  detail?: string
  /**  unix ms when this toast auto-dismisses; falsy = sticky. */
  expiresAt?: number
}

type State = {
  items: ToastEntry[]
}

const state = reactive<State>({ items: [] })
let _seq = 1

const DEFAULT_TTL_MS: Record<ToastLevel, number> = {
  info: 3500,
  success: 3000,
  warn: 5000,
  error: 6500,
}

const pruneExpired = () => {
  const now = Date.now()
  state.items = state.items.filter(t => !t.expiresAt || t.expiresAt > now)
}

let _pruneTimer: number | null = null

const schedulePrune = () => {
  if (_pruneTimer != null) return
  _pruneTimer = window.setInterval(() => {
    pruneExpired()
    if (!state.items.length && _pruneTimer != null) {
      window.clearInterval(_pruneTimer)
      _pruneTimer = null
    }
  }, 500)
}

export const pushToast = (level: ToastLevel, title: string, detail?: string) => {
  const id = _seq++
  const ttl = DEFAULT_TTL_MS[level]
  state.items.push({
    id,
    level,
    title,
    detail,
    expiresAt: ttl ? Date.now() + ttl : undefined,
  })
  schedulePrune()
  return id
}

export const dismissToast = (id: number) => {
  state.items = state.items.filter(t => t.id !== id)
}

export const useToast = () => ({
  toasts: readonly(state).items,
  push: pushToast,
  dismiss: dismissToast,
  info: (title: string, detail?: string) => pushToast('info', title, detail),
  success: (title: string, detail?: string) => pushToast('success', title, detail),
  warn: (title: string, detail?: string) => pushToast('warn', title, detail),
  error: (title: string, detail?: string) => pushToast('error', title, detail),
})
