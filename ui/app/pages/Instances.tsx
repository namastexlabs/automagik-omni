import { useState, useEffect } from 'react'
import { useConveyor } from '@/app/hooks/use-conveyor'
import { Button } from '@/app/components/ui/button'
import { InstanceTable } from '@/app/components/instances/InstanceTable'
import { CreateInstanceDialog } from '@/app/components/instances/CreateInstanceDialog'
import { QRCodeDialog } from '@/app/components/instances/QRCodeDialog'
import { DeleteInstanceDialog } from '@/app/components/instances/DeleteInstanceDialog'
import type { Instance } from '@/lib/conveyor/schemas/omni-schema'

export default function Instances() {
  const { omni } = useConveyor()
  const [instances, setInstances] = useState<Instance[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const [createDialogOpen, setCreateDialogOpen] = useState(false)
  const [qrDialogOpen, setQrDialogOpen] = useState(false)
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false)
  const [selectedInstance, setSelectedInstance] = useState<string | null>(null)

  const loadInstances = async () => {
    try {
      setLoading(true)
      setError(null)
      const data = await omni.listInstances()
      setInstances(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load instances')
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
          <div className="bg-red-900/50 border border-red-500 text-red-200 px-4 py-3 rounded mb-4">
            {error}
          </div>
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
