import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  vpnApi, jobsApi, shipsApi, shipEntitiesApi, detectionApi, classifyApi, trainingApi, augmentApi, statsApi, urlsApi,
} from '@/api/client.ts'
import type { JobCreate } from '@/types/index.ts'

// Stats
export const useStats = () =>
  useQuery({ queryKey: ['stats'], queryFn: statsApi.get, refetchInterval: 30000 })

// VPN connection (direct + VPN IP, server, country) — live
export const useVPNConnection = () =>
  useQuery({ queryKey: ['vpn-connection'], queryFn: vpnApi.connection, refetchInterval: 20000 })

export const useVPNConfig = () => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: { enabled?: boolean; proxy_country?: string }) => vpnApi.setConfig(data),
    onSuccess: (data) => {
      // apply immediately, then refetch to confirm the live IPs
      qc.setQueryData(['vpn-connection'], data)
      qc.invalidateQueries({ queryKey: ['vpn-connection'] })
    },
  })
}

// Jobs
export const useJobs = () =>
  useQuery({ queryKey: ['jobs'], queryFn: jobsApi.list, refetchInterval: 5000 })

export const useCreateJob = () => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: JobCreate) => jobsApi.create(data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['jobs'] }),
  })
}

export const useStartJob = () => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: number) => jobsApi.start(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['jobs'] }),
  })
}

export const usePauseJob = () => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: number) => jobsApi.pause(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['jobs'] }),
  })
}

export const useDeleteJob = () => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: number) => jobsApi.delete(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['jobs'] }),
  })
}

export const useAnalyze = () =>
  useMutation({ mutationFn: (url: string) => jobsApi.analyze(url) })

// Ships
export const useShips = (params: { type?: string; source?: string; search?: string; page?: number; per_page?: number }) =>
  useQuery({
    queryKey: ['ships', params],
    queryFn: () => shipsApi.list(params),
  })

export const useShip = (id: number | null) =>
  useQuery({
    queryKey: ['ship', id],
    queryFn: () => shipsApi.get(id!),
    enabled: id !== null,
  })

// Ship Entities (v2 — grouped)
export const useShipEntities = (params: { search?: string; ship_type?: string; source?: string; page?: number; per_page?: number }) =>
  useQuery({
    queryKey: ['ship-entities', params],
    queryFn: () => shipEntitiesApi.list(params),
  })

export const useShipEntity = (id: number | null) =>
  useQuery({
    queryKey: ['ship-entity', id],
    queryFn: () => shipEntitiesApi.get(id!),
    enabled: id !== null,
  })

export const useBackfillShips = () => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: shipEntitiesApi.backfill,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['ship-entities'] }),
  })
}

// Detection
export const useDetectShip = () => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (shipId: number) => detectionApi.detectShip(shipId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['ship-entity'] })
      qc.invalidateQueries({ queryKey: ['ship-entities'] })
    },
  })
}

// Classification
export const useClassifyUpload = () => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (file: File) => classifyApi.upload(file),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['classifications'] })
      qc.invalidateQueries({ queryKey: ['stats'] })
    },
  })
}

export const useClassifyShip = () => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: number) => classifyApi.ship(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['ships'] })
      qc.invalidateQueries({ queryKey: ['classifications'] })
    },
  })
}

export const useClassifications = (page = 1) =>
  useQuery({
    queryKey: ['classifications', page],
    queryFn: () => classifyApi.history({ page, per_page: 20 }),
  })

export const useModelInfo = () =>
  useQuery({ queryKey: ['model-info'], queryFn: classifyApi.modelInfo })

// Training
export const useTrainingStatus = () =>
  useQuery({
    queryKey: ['training-status'],
    queryFn: trainingApi.status,
    refetchInterval: (query) => query.state.data?.running ? 3000 : false,
  })

export const useStartTraining = () =>
  useMutation({ mutationFn: trainingApi.start })

export const useDatasets = () =>
  useQuery({ queryKey: ['datasets'], queryFn: trainingApi.datasets })

// Augmentation
export const useAugmentStatus = () =>
  useQuery({
    queryKey: ['augment-status'],
    queryFn: augmentApi.status,
    refetchInterval: (query) => query.state.data?.running ? 2000 : false,
  })

export const useStartAugment = () =>
  useMutation({ mutationFn: augmentApi.start })

// URLs
export const useUrls = () =>
  useQuery({ queryKey: ['urls'], queryFn: urlsApi.list })

export const useAddUrl = () => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ url, name }: { url: string; name?: string }) => urlsApi.add(url, name),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['urls'] }),
  })
}

export const useDeleteUrl = () => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: number) => urlsApi.delete(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['urls'] }),
  })
}
