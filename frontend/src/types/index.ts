export interface Job {
  id: number
  url: string
  name: string | null
  status: string
  total_items: number
  downloaded: number
  limit_count: number | null
  delay_min: number
  delay_max: number
  vpn_required: number | boolean
  created_at: string | null
  started_at: string | null
  completed_at: string | null
  error_message: string | null
}

export interface JobCreate {
  url: string
  name?: string
  limit?: number
  delay_min?: number
  delay_max?: number
  vpn_required?: boolean
}

export interface Ship {
  id: number
  job_id: number
  source_url: string
  image_url: string | null
  local_path: string | null
  ship_name: string | null
  ship_type: string | null
  imo_number: string | null
  mmsi: string | null
  metadata: unknown
  status: string
  created_at: string | null
  downloaded_at: string | null
  error_message: string | null
  job_name?: string | null
  job_url?: string | null
}

export interface ShipListResponse {
  ships: Ship[]
  types: string[]
  total: number
  page: number
  per_page: number
  pages: number
}

export interface VPNStatus {
  connected: boolean
  country?: string | null
  ip?: string | null
  raw?: string
  error?: string
}

export interface Prediction {
  label: string
  confidence: number
}

export interface ClassifyResponse {
  predictions: Prediction[]
  image_path: string
  filename: string
}

export interface ClassificationRecord {
  id: number
  item_id: number | null
  image_path: string | null
  predicted_type: string
  confidence: number
  all_predictions: Prediction[] | string | null
  model_name: string | null
  created_at: string | null
}

export interface Stats {
  total_jobs: number
  total_items: number
  downloaded: number
  pending: number
  failed: number
  classifications: number
  type_distribution: { type: string; count: number }[]
}

export interface TypeStat {
  type: string
  count: number
  sources: number
}

export interface ShipStats {
  total_downloaded: number
  total_classified: number
  by_type: TypeStat[]
}

export interface AnalyzeResult {
  success: boolean
  title?: string
  categories?: { name: string; url: string }[]
  url?: string
  error?: string
}

export interface PredefinedURL {
  id: number
  url: string
  name: string | null
  created_at: string | null
}

export interface ModelInfo {
  loaded: boolean
  model_name?: string
  num_labels?: number
  labels?: string[]
  accuracy?: string
  local_path?: string
  checkpoints?: string[]
}

export interface TrainingStatus {
  running: boolean
  progress: number
  message: string
  epoch?: number
  total_epochs?: number
}

export interface AugmentStatus {
  running: boolean
  progress: number
  message: string
  generated?: number
  total?: number
}

export type TabId = 'dashboard' | 'scraper' | 'ships' | 'classify' | 'training' | 'settings'
