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
  sources: string[]
  total: number
  page: number
  per_page: number
  pages: number
}

export interface VPNConnection {
  vpn_enabled: boolean
  token_present: boolean
  direct_ip: string | null
  vpn_ip: string | null
  proxy_country: string | null
  server_host: string | null
  available_countries: string[]
  protected: boolean
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
  total_ships: number
  total_images: number
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

// ---- v2 Ship Entities (grouped) ----

export interface ShipEntity {
  id: number
  name: string
  canonical_name: string | null
  ship_type: string | null
  ship_class: string | null
  flag: string | null
  imo: string | null
  mmsi: string | null
  year_built: number | null
  operator: string | null
  country: string | null
  image_count: number
  thumbnail: string | null
  created_at: string | null
  updated_at: string | null
}

export interface ShipImage {
  id: number
  file_path: string
  src: string | null
  source_url: string | null
  source_name: string | null
  file_size: number | null
  width: number | null
  height: number | null
  quality_score: number | null
  is_synthetic: boolean
  parent_image_id: number | null
  is_primary_crop: boolean
  crop_rank: number | null
  has_crops: boolean
  created_at: string | null
}

export interface DetectionResult {
  ship_id: number
  ship_name: string
  images_processed: number
  detections_found: number
  crops_created: number
}

export interface DetectionStatus {
  running: boolean
  progress: number
  total: number
  message: string
}

export interface ShipAlias {
  id: number
  alias_name: string
  source: string | null
}

export interface ShipEntityDetail extends ShipEntity {
  images: ShipImage[]
  aliases: ShipAlias[]
  sources: string[]
  description: string | null
  notes: string | null
  subtype: string | null
}

export interface ShipEntityListResponse {
  ships: ShipEntity[]
  types: string[]
  sources: string[]
  total: number
  page: number
  per_page: number
  pages: number
}

// Visual similarity / specific-ship recognition (DINOv2)
export interface SimilarityMatch {
  image_id: number
  ship_id: number | null
  file_path: string
  src: string | null
  ship_type: string | null
  ship_name: string | null
  similarity: number
}

export interface SimilarityBestMatch {
  ship_id: number | null
  ship_name: string | null
  ship_type?: string | null
  confidence: number
  margin: number
  confident: boolean
  reason: string
}

export interface SimilarityOcr {
  available: boolean
  text: string
  confirms?: boolean
  matched_on?: string | null
  note?: string
}

export interface SimilarityResponse {
  results: SimilarityMatch[]
  best_match: SimilarityBestMatch
  method: string
  model: string
  threshold: number
  gallery_size: number | null
  ocr?: SimilarityOcr
}

export interface ReidReadiness {
  min_images: number
  total_ships_with_images: number
  qualifying_ships: number
  usable_images: number
  ready: boolean
  has_trained_model: boolean
}

export interface ReidStatus {
  running: boolean
  progress: number
  message: string
  num_classes?: number
  samples?: number
  final_loss?: number
}
