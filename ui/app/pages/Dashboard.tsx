import { useState, useEffect } from 'react'
import { useConveyor } from '@/app/hooks/use-conveyor'
import { Button } from '@/app/components/ui/button'
import { Badge } from '@/app/components/ui/badge'
import type { BackendStatus, HealthCheck } from '@/lib/conveyor/schemas/backend-schema'

export default function Dashboard() {
  const { backend } = useConveyor()
  const [status, setStatus] = useState<BackendStatus | null>(null)
  const [health, setHealth] = useState<HealthCheck | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [showInfoBanner, setShowInfoBanner] = useState(true)

  const loadStatus = async () => {
    // Skip if not in Electron context
    if (!backend || !backend.status || !backend.health) {
      setError('Backend controls only available in Electron app')
      return
    }

    try {
      setLoading(true)
      setError(null)
      const [statusData, healthData] = await Promise.all([backend.status(), backend.health()])
      setStatus(statusData)
      setHealth(healthData)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load status')
    } finally {
      setLoading(false)
    }
  }

  const handleStart = async () => {
    if (!backend || !backend.start) return

    try {
      setLoading(true)
      setError(null)
      const result = await backend.start()
      if (result.success) {
        // Wait for PM2 to fully start processes (2 seconds)
        await new Promise((resolve) => setTimeout(resolve, 2000))
        await loadStatus()
      } else {
        setError(result.message)
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to start backend')
    } finally {
      setLoading(false)
    }
  }

  const handleStop = async () => {
    if (!backend || !backend.stop) return

    try {
      setLoading(true)
      setError(null)
      const result = await backend.stop()
      if (result.success) {
        // Wait for PM2 to fully stop (1 second)
        await new Promise((resolve) => setTimeout(resolve, 1000))
        await loadStatus()
      } else {
        setError(result.message)
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to stop backend')
    } finally {
      setLoading(false)
    }
  }

  const handleRestart = async () => {
    if (!backend || !backend.restart) return

    try {
      setLoading(true)
      setError(null)
      const result = await backend.restart()
      if (result.success) {
        // Wait for PM2 to restart (3 seconds)
        await new Promise((resolve) => setTimeout(resolve, 3000))
        await loadStatus()
      } else {
        setError(result.message)
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to restart backend')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadStatus()
    const interval = setInterval(loadStatus, 10000) // Poll every 10s
    return () => clearInterval(interval)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  return (
    <div className="h-screen bg-black text-white overflow-auto">
      <div className="max-w-6xl mx-auto p-8">
        <h1 className="text-4xl font-bold mb-8">Automagik Omni Dashboard</h1>

        {error && (
          <div className="bg-red-900/50 border border-red-500 text-red-200 px-4 py-3 rounded mb-4">
            {error}
          </div>
        )}

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-8 auto-rows-fr">
          {/* API Status Card */}
          <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-6 flex flex-col">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-xl font-semibold">FastAPI</h2>
              <Badge variant={status?.api.healthy ? 'default' : 'destructive'}>
                {status?.api.running ? (status.api.healthy ? 'Healthy' : 'Unhealthy') : 'Stopped'}
              </Badge>
            </div>
            {status?.api.running && (
              <div className="text-sm text-zinc-400 mt-auto">
                <p>Port: {status.api.port}</p>
                <p className="truncate">URL: {status.api.url}</p>
              </div>
            )}
          </div>

          {/* Discord Bot Card */}
          <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-6 flex flex-col">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-xl font-semibold">Discord Bot</h2>
              <Badge variant={status?.discord.healthy ? 'default' : 'destructive'}>
                {status?.discord.running
                  ? status.discord.healthy
                    ? 'Healthy'
                    : 'Unhealthy'
                  : 'Stopped'}
              </Badge>
            </div>
          </div>

          {/* PM2 Status Card */}
          <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-6 flex flex-col min-w-0">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-xl font-semibold">Process Manager</h2>
              <div className="flex gap-2">
                {status?.pm2.mode && (
                  <Badge variant="outline" className="text-xs">
                    {status.pm2.mode === 'pm2' ? 'PM2' : 'Direct'}
                  </Badge>
                )}
                <Badge variant={status?.pm2.running ? 'default' : 'destructive'}>
                  {status?.pm2.running ? `${status.pm2.processes.length} Running` : 'Stopped'}
                </Badge>
              </div>
            </div>
            {status?.pm2.processes && status.pm2.processes.length > 0 ? (
              <div className="text-sm text-zinc-400 space-y-2">
                {status.pm2.processes.map((proc) => (
                  <div key={proc.name} className="flex items-center justify-between gap-2 min-w-0">
                    <span className="truncate flex-1 font-mono text-xs">
                      {proc.name}
                    </span>
                    <Badge
                      variant={proc.status === 'online' ? 'default' : 'destructive'}
                      className="shrink-0"
                    >
                      {proc.status}
                    </Badge>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-sm text-zinc-400">
                {status?.api.running
                  ? '⚡ Running via direct process'
                  : 'No processes detected'}
              </div>
            )}
          </div>
        </div>

        {/* Health Check Info */}
        {health && (
          <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-6 mb-8">
            <h2 className="text-xl font-semibold mb-4">System Health</h2>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div>
                <p className="text-sm text-zinc-400">API</p>
                <Badge variant={health.services.api ? 'default' : 'destructive'}>
                  {health.services.api ? 'OK' : 'Down'}
                </Badge>
              </div>
              <div>
                <p className="text-sm text-zinc-400">Discord</p>
                <Badge variant={health.services.discord ? 'default' : 'destructive'}>
                  {health.services.discord ? 'OK' : 'Down'}
                </Badge>
              </div>
              <div>
                <p className="text-sm text-zinc-400">Database</p>
                <Badge variant={health.services.database ? 'default' : 'destructive'}>
                  {health.services.database ? 'OK' : 'Down'}
                </Badge>
              </div>
            </div>
            <div className="mt-4 text-sm text-zinc-400">
              Last checked: {new Date(health.timestamp).toLocaleString()}
            </div>
          </div>
        )}

        {/* Control Buttons */}
        <div className="flex gap-4 flex-wrap">
          <Button onClick={handleStart} disabled={loading || status?.api.running}>
            {status?.api.running ? '✓ Backend Running' : 'Start Backend'}
          </Button>
          <Button
            onClick={handleStop}
            disabled={loading || !status?.api.running || status?.pm2.mode === 'direct'}
            variant="destructive"
          >
            Stop Backend
          </Button>
          <Button
            onClick={handleRestart}
            disabled={loading || !status?.api.running || status?.pm2.mode === 'direct'}
            variant="outline"
          >
            Restart Backend
          </Button>
          <Button onClick={loadStatus} disabled={loading} variant="outline">
            Refresh Status
          </Button>
        </div>

        {status?.pm2.mode === 'direct' && status?.api.running && showInfoBanner && (
          <div className="mt-4 p-4 bg-blue-900/20 border border-blue-600/30 rounded-lg max-w-full relative">
            <button
              onClick={() => setShowInfoBanner(false)}
              className="absolute top-2 right-2 text-blue-200 hover:text-blue-100 text-xl leading-none"
              aria-label="Dismiss"
            >
              ×
            </button>
            <p className="text-sm text-blue-200 break-words pr-6">
              ℹ️ Backend is running in <strong>Direct Process</strong> mode (PM2 not available).
              Process management is handled by the Electron application.
            </p>
          </div>
        )}

        {loading && (
          <div className="mt-4 text-zinc-400">
            <p>Loading...</p>
          </div>
        )}
      </div>
    </div>
  )
}
