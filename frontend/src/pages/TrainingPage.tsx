import { useState } from 'react'
import {
  useTrainingStatus, useStartTraining, useDatasets,
  useAugmentStatus, useStartAugment,
} from '@/hooks/useApi.ts'
import { Card } from '@/components/ui/Card.tsx'
import { Button } from '@/components/ui/Button.tsx'
import { ProgressBar } from '@/components/ui/ProgressBar.tsx'

export function TrainingPage() {
  const { data: trainingStatus } = useTrainingStatus()
  const { data: augmentStatus } = useAugmentStatus()
  const { data: datasetsData } = useDatasets()
  const startTraining = useStartTraining()
  const startAugment = useStartAugment()

  const [datasetDir, setDatasetDir] = useState('')
  const [epochs, setEpochs] = useState(5)
  const [batchSize, setBatchSize] = useState(8)
  const [learningRate, setLearningRate] = useState(0.00005)

  const [augSourceDir, setAugSourceDir] = useState('')
  const [augCount, setAugCount] = useState(5)
  const [transforms, setTransforms] = useState({
    horizontal_flip: true,
    rotation: true,
    color_jitter: true,
    random_crop: true,
    gaussian_blur: false,
    perspective: false,
  })

  const handleStartTraining = () => {
    if (!datasetDir) return
    startTraining.mutate({ dataset_dir: datasetDir, epochs, batch_size: batchSize, learning_rate: learningRate })
  }

  const handleStartAugment = () => {
    if (!augSourceDir) return
    startAugment.mutate({ source_dir: augSourceDir, num_per_image: augCount, transforms })
  }

  const datasets = (datasetsData as { datasets?: { name: string; path: string; classes: number; images: number }[] })?.datasets ?? []

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Training & Augmentation</h1>

      <div className="grid md:grid-cols-2 gap-6">
        {/* Training */}
        <Card>
          <h2 className="text-lg font-semibold mb-3">Modell-Training</h2>
          <div className="space-y-3">
            <div>
              <label className="text-xs text-[var(--text-muted)]">Dataset-Verzeichnis</label>
              <input type="text" value={datasetDir} onChange={(e) => setDatasetDir(e.target.value)}
                placeholder="/pfad/zum/dataset"
                className="w-full bg-[var(--bg)] border border-[var(--border)] rounded px-3 py-2 text-sm" />
            </div>
            <div className="grid grid-cols-3 gap-2">
              <div>
                <label className="text-xs text-[var(--text-muted)]">Epochen</label>
                <input type="number" value={epochs} onChange={(e) => setEpochs(+e.target.value)}
                  className="w-full bg-[var(--bg)] border border-[var(--border)] rounded px-2 py-1 text-sm" />
              </div>
              <div>
                <label className="text-xs text-[var(--text-muted)]">Batch Size</label>
                <input type="number" value={batchSize} onChange={(e) => setBatchSize(+e.target.value)}
                  className="w-full bg-[var(--bg)] border border-[var(--border)] rounded px-2 py-1 text-sm" />
              </div>
              <div>
                <label className="text-xs text-[var(--text-muted)]">Learning Rate</label>
                <input type="number" step="0.00001" value={learningRate} onChange={(e) => setLearningRate(+e.target.value)}
                  className="w-full bg-[var(--bg)] border border-[var(--border)] rounded px-2 py-1 text-sm" />
              </div>
            </div>
            <Button onClick={handleStartTraining}
              disabled={!datasetDir || startTraining.isPending || trainingStatus?.running}>
              {trainingStatus?.running ? 'Training läuft...' : 'Training starten'}
            </Button>

            {trainingStatus?.running && (
              <div className="mt-2">
                <ProgressBar value={trainingStatus.progress} label={trainingStatus.message} />
              </div>
            )}
            {!trainingStatus?.running && trainingStatus?.message && trainingStatus.message !== 'Idle' && (
              <p className="text-sm text-[var(--text-muted)]">{trainingStatus.message}</p>
            )}
          </div>
        </Card>

        {/* Augmentation */}
        <Card>
          <h2 className="text-lg font-semibold mb-3">Daten-Augmentation</h2>
          <div className="space-y-3">
            <div>
              <label className="text-xs text-[var(--text-muted)]">Quell-Verzeichnis</label>
              <input type="text" value={augSourceDir} onChange={(e) => setAugSourceDir(e.target.value)}
                placeholder="/pfad/zum/bilder"
                className="w-full bg-[var(--bg)] border border-[var(--border)] rounded px-3 py-2 text-sm" />
            </div>
            <div>
              <label className="text-xs text-[var(--text-muted)]">Bilder pro Original</label>
              <input type="number" value={augCount} onChange={(e) => setAugCount(+e.target.value)}
                className="w-full bg-[var(--bg)] border border-[var(--border)] rounded px-2 py-1 text-sm" />
            </div>
            <div className="grid grid-cols-2 gap-2">
              {Object.entries(transforms).map(([key, val]) => (
                <label key={key} className="flex items-center gap-2 text-sm cursor-pointer">
                  <input type="checkbox" checked={val}
                    onChange={(e) => setTransforms({ ...transforms, [key]: e.target.checked })} />
                  {key.replace(/_/g, ' ')}
                </label>
              ))}
            </div>
            <Button onClick={handleStartAugment}
              disabled={!augSourceDir || startAugment.isPending || augmentStatus?.running}>
              {augmentStatus?.running ? 'Augmentation läuft...' : 'Augmentation starten'}
            </Button>

            {augmentStatus?.running && (
              <div className="mt-2">
                <ProgressBar value={augmentStatus.progress} label={augmentStatus.message} />
              </div>
            )}
          </div>
        </Card>
      </div>

      {/* Available Datasets */}
      <Card>
        <h2 className="text-lg font-semibold mb-3">Verfügbare Datasets</h2>
        {datasets.length ? (
          <div className="space-y-2">
            {datasets.map((ds: { name: string; path: string; classes: number; images: number }) => (
              <div key={ds.path} className="flex items-center justify-between bg-[var(--bg)] rounded p-2 text-sm">
                <div>
                  <span className="font-medium">{ds.name}</span>
                  <span className="text-[var(--text-muted)] ml-2">{ds.classes} Klassen, {ds.images} Bilder</span>
                </div>
                <Button size="sm" variant="ghost" onClick={() => setDatasetDir(ds.path)}>Verwenden</Button>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-sm text-[var(--text-muted)]">Keine Datasets gefunden</p>
        )}
      </Card>
    </div>
  )
}
