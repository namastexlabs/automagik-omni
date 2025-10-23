import { useState, useEffect } from 'react'
import { useConveyor } from '@/app/hooks/use-conveyor'
import { Button } from '@/app/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/app/components/ui/card'
import { InstanceTable } from '@/app/components/instances/InstanceTable'
import { CreateInstanceDialog } from '@/app/components/instances/CreateInstanceDialog'
import { EditInstanceDialog } from '@/app/components/instances/EditInstanceDialog'
import { QRCodeDialog } from '@/app/components/instances/QRCodeDialog'
import { DeleteInstanceDialog } from '@/app/components/instances/DeleteInstanceDialog'
import { getErrorMessage, isBackendError, isBackendStarting } from '@/lib/utils/error'
import type { Instance } from '@/lib/conveyor/schemas/omni-schema'

export default function Instances() {
  const { omni } = useConveyor()
  const [instances, setInstances] = useState<Instance[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const [createDialogOpen, setCreateDialogOpen] = useState(false)
  const [editDialogOpen, setEditDialogOpen] = useState(false)
  const [qrDialogOpen, setQrDialogOpen] = useState(false)
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false)
  const [selectedInstance, setSelectedInstance] = useState<string | null>(null)
  const [selectedInstanceData, setSelectedInstanceData] = useState<Instance | null>(null)

  const loadInstances = async () => {
    try {
      setLoading(true)
      setError(null)
      const data = await omni.listInstances()
      setInstances(data)
    } catch (err) {
      const errorMessage = getErrorMessage(err)
      setError(errorMessage)
      console.error('Failed to load instances:', err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadInstances()
    const interval = setInterval(loadInstances, 15000) // Poll every 15s
    return () => clearInterval(interval)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const handleEdit = (instance: Instance) => {
    setSelectedInstanceData(instance)
    setEditDialogOpen(true)
  }

  const handleShowQR = (instanceName: string) => {
    setSelectedInstance(instanceName)
    setQrDialogOpen(true)
  }

  const handleDelete = (instanceName: string) => {
    setSelectedInstance(instanceName)
    setDeleteDialogOpen(true)
  }

  const handleDeleted = () => {
    loadInstances()
  }

  const handleCreated = () => {
    loadInstances()
  }

  const handleUpdated = () => {
    loadInstances()
  }

  return (
    <div className="h-screen bg-black text-white overflow-auto">
      <div className="max-w-7xl mx-auto p-8">
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-4xl font-bold">Instances</h1>
            <p className="text-zinc-400 mt-2">
              Manage your messaging instances (WhatsApp, Discord)
            </p>
          </div>
          <Button onClick={() => setCreateDialogOpen(true)} disabled={loading}>
            Create Instance
          </Button>
        </div>

        {error && (
          <Card className={`mb-6 ${isBackendStarting(new Error(error)) ? 'border-blue-500 bg-blue-900/20' : 'border-red-500 bg-red-900/20'}`}>
            <CardHeader>
              <CardTitle className={`text-xl flex items-center gap-2 ${isBackendStarting(new Error(error)) ? 'text-blue-400' : 'text-red-400'}`}>
                <span className="text-2xl">{isBackendStarting(new Error(error)) ? '⏳' : '⚠️'}</span>
                {isBackendStarting(new Error(error)) ? 'Backend Starting Up' : 'Failed to Load Instances'}
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <p className={isBackendStarting(new Error(error)) ? 'text-blue-200' : 'text-red-200'}>{error}</p>
              <div className="flex items-center gap-3">
                <Button onClick={loadInstances} variant="outline" disabled={loading}>
                  {loading ? 'Retrying...' : 'Retry'}
                </Button>
                <Button onClick={() => setError(null)} variant="ghost">
                  Dismiss
                </Button>
              </div>
              {isBackendStarting(new Error(error)) && (
                <p className="text-sm text-blue-300 mt-2">
                  ⏱️ <strong>Auto-retrying:</strong> The backend is initializing. Instances will load automatically when ready.
                </p>
              )}
              {isBackendError(new Error(error)) && !isBackendStarting(new Error(error)) && (
                <p className="text-sm text-zinc-400 mt-2">
                  💡 <strong>Tip:</strong> Go to Dashboard and start the backend service
                </p>
              )}
            </CardContent>
          </Card>
        )}

        {loading && instances.length === 0 ? (
          <div className="flex items-center justify-center h-64">
            <div className="text-zinc-400">Loading instances...</div>
          </div>
        ) : (
          <>
            <InstanceTable
              instances={instances}
              onRefresh={loadInstances}
              onShowQR={handleShowQR}
              onDelete={handleDelete}
              onEdit={handleEdit}
            />

            <div className="mt-4 flex items-center justify-between">
              <div className="text-sm text-zinc-400">
                {instances.length === 0
                  ? 'No instances'
                  : `${instances.length} instance${instances.length === 1 ? '' : 's'}`}
              </div>
              <Button variant="outline" onClick={loadInstances} disabled={loading}>
                {loading ? 'Refreshing...' : 'Refresh'}
              </Button>
            </div>
          </>
        )}

        <CreateInstanceDialog
          open={createDialogOpen}
          onOpenChange={setCreateDialogOpen}
          onCreated={handleCreated}
        />

        <EditInstanceDialog
          instance={selectedInstanceData}
          open={editDialogOpen}
          onOpenChange={setEditDialogOpen}
          onUpdated={handleUpdated}
        />

        <QRCodeDialog
          instanceName={selectedInstance}
          open={qrDialogOpen}
          onOpenChange={setQrDialogOpen}
        />

        <DeleteInstanceDialog
          instanceName={selectedInstance}
          open={deleteDialogOpen}
          onOpenChange={setDeleteDialogOpen}
          onDeleted={handleDeleted}
        />
      </div>
    </div>
  )
}
