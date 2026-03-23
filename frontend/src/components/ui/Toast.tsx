import { useState, useEffect, useCallback } from 'react'

interface ToastData {
  id: number
  type: 'success' | 'error'
  message: string
}

let toastId = 0
let addToastGlobal: ((type: 'success' | 'error', message: string) => void) | null = null

export function showToast(type: 'success' | 'error', message: string) {
  addToastGlobal?.(type, message)
}

export function ToastContainer() {
  const [toasts, setToasts] = useState<ToastData[]>([])

  const addToast = useCallback((type: 'success' | 'error', message: string) => {
    const id = ++toastId
    setToasts((prev) => [...prev, { id, type, message }])
    setTimeout(() => setToasts((prev) => prev.filter((t) => t.id !== id)), 4000)
  }, [])

  useEffect(() => {
    addToastGlobal = addToast
    return () => { addToastGlobal = null }
  }, [addToast])

  if (!toasts.length) return null

  return (
    <div className="fixed top-4 right-4 z-[100] space-y-2">
      {toasts.map((t) => (
        <div
          key={t.id}
          className={`flex items-center gap-3 px-4 py-3 rounded-lg shadow-lg text-sm font-medium animate-slide-in ${
            t.type === 'success'
              ? 'bg-emerald-600 text-white'
              : 'bg-red-600 text-white'
          }`}
        >
          <span className="text-lg">
            {t.type === 'success' ? '\u2714' : '\u2718'}
          </span>
          <span>{t.message}</span>
        </div>
      ))}
    </div>
  )
}
