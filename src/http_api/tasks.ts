import { get } from './client'

export type BackgroundTask = {
  id: string
  task_type: string
  status: 'pending' | 'running' | 'done' | 'error'
  progress: number
  stage: string | null
  result: unknown
  error: string | null
  created_at: number
  updated_at: number
}

export const getTaskApi = (taskId: string) => get<BackgroundTask>(`/tasks/${taskId}`)

export const listTasksApi = (taskType?: string, limit = 20) =>
  get<BackgroundTask[]>(`/tasks${taskType ? `?task_type=${taskType}&limit=${limit}` : `?limit=${limit}`}`)
