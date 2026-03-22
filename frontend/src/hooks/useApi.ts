import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  vpnApi, jobsApi, shipsApi, classifyApi, trainingApi, augmentApi, statsApi, urlsApi,
} from '@/api/client.ts'
import type { JobCreate } from '@/types/index.ts'

// Stats
export const useStats = () =>
  useQuery({ queryKey: ['stats'], queryFn: statsApi.get, refetchInterval: 30000 })

// VPN
export const useVPNStatus = () =>
  useQuery({ queryKey: ['vpn-status'], queryFn: vpnApi.status, refetchInterval: 30000 })

export const useVPNConnect = () => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (country: string) => vpnApi.connect(country),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['vpn-status'] }),
  })
}

export const useVPNDisconnect = () => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: vpnApi.disconnect,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['vpn-status'] }),
  })
}

export const useVPNRotate = () => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: vpnApi.rotate,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['vpn-status'] }),
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
export const useShips = (params: { type?: string; search?: string; page?: number }) =>
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
