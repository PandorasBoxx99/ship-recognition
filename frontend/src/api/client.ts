import axios from 'axios'
import type {
  AnalyzeResult, AugmentStatus, ClassificationRecord, ClassifyResponse,
  Job, JobCreate, ModelInfo, PredefinedURL, Prediction, Ship, ShipListResponse,
  ShipStats, Stats, TrainingStatus, VPNStatus,
} from '@/types/index.ts'

const client = axios.create({ baseURL: '' })

// VPN
export const vpnApi = {
  status: () => client.get<VPNStatus>('/api/vpn/status').then(r => r.data),
  connect: (country: string) => client.post<VPNStatus>('/api/vpn/connect', { country }).then(r => r.data),
  disconnect: () => client.post<VPNStatus>('/api/vpn/disconnect').then(r => r.data),
  rotate: () => client.post<VPNStatus>('/api/vpn/rotate').then(r => r.data),
}

// Jobs
export const jobsApi = {
  list: () => client.get<Job[]>('/api/jobs').then(r => r.data),
  get: (id: number) => client.get<{ job: Job; items: Ship[] }>(`/api/jobs/${id}`).then(r => r.data),
  create: (data: JobCreate) => client.post<Job>('/api/jobs', data).then(r => r.data),
  start: (id: number) => client.post(`/api/jobs/${id}/start`).then(r => r.data),
  pause: (id: number) => client.post(`/api/jobs/${id}/pause`).then(r => r.data),
  delete: (id: number) => client.delete(`/api/jobs/${id}/delete`).then(r => r.data),
  analyze: (url: string) => client.post<AnalyzeResult>('/api/analyze', { url }).then(r => r.data),
}

// Ships
export const shipsApi = {
  list: (params: { type?: string; search?: string; page?: number; per_page?: number }) =>
    client.get<ShipListResponse>('/api/ships', { params }).then(r => r.data),
  get: (id: number) => client.get<Ship>(`/api/ships/${id}`).then(r => r.data),
  stats: () => client.get<ShipStats>('/api/ships/stats').then(r => r.data),
}

// Classification
export const classifyApi = {
  upload: (file: File) => {
    const fd = new FormData()
    fd.append('image', file)
    return client.post<ClassifyResponse>('/api/classify', fd).then(r => r.data)
  },
  ship: (id: number) => client.post<{ ship_id: number; predictions: Prediction[] }>(`/api/classify/ship/${id}`).then(r => r.data),
  history: (params?: { page?: number; per_page?: number }) =>
    client.get<{ classifications: ClassificationRecord[]; total: number; page: number; pages: number }>('/api/classifications', { params }).then(r => r.data),
  modelInfo: () => client.get<ModelInfo>('/api/model/info').then(r => r.data),
}

// Training
export const trainingApi = {
  status: () => client.get<TrainingStatus>('/api/training/status').then(r => r.data),
  start: (data: { dataset_dir: string; epochs?: number; batch_size?: number; learning_rate?: number }) =>
    client.post('/api/training/start', data).then(r => r.data),
  datasets: () => client.get('/api/training/datasets').then(r => r.data),
}

// Augmentation
export const augmentApi = {
  start: (data: { source_dir: string; num_per_image?: number; transforms?: Record<string, unknown> }) =>
    client.post('/api/augment', data).then(r => r.data),
  status: () => client.get<AugmentStatus>('/api/augment/status').then(r => r.data),
}

// Stats
export const statsApi = {
  get: () => client.get<Stats>('/api/stats').then(r => r.data),
}

// URLs / Settings
export const urlsApi = {
  list: () => client.get<PredefinedURL[]>('/api/urls').then(r => r.data),
  add: (url: string, name?: string) => client.post<PredefinedURL>('/api/urls', { url, name }).then(r => r.data),
  delete: (id: number) => client.delete(`/api/urls/${id}`).then(r => r.data),
}
