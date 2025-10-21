import { useState, useEffect } from 'react'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/app/components/ui/dialog'
import { Button } from '@/app/components/ui/button'
import { useConveyor } from '@/app/hooks/use-conveyor'

interface QRCodeDialogProps {
  instanceName: string | null
  open: boolean
  onOpenChange: (open: boolean) => void
}

export function QRCodeDialog({ instanceName, open, onOpenChange }: QRCodeDialogProps) {
  const { omni } = useConveyor()
  const [qrCode, setQrCode] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (open && instanceName) {
      loadQRCode()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, instanceName])

  const loadQRCode = async () => {
    if (!instanceName) return

    try {
      setLoading(true)
      setError(null)
      const result = await omni.getInstanceQR(instanceName)
      // Backend returns base64 data URL (e.g., data:image/png;base64,...)
      const qrImageData = result.qr_code || result.base64
      setQrCode(qrImageData)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load QR code')
    } finally {
      setLoading(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Scan QR Code</DialogTitle>
          <DialogDescription>
            Scan this QR code with WhatsApp to connect the instance: {instanceName}
          </DialogDescription>
        </DialogHeader>

        <div className="flex flex-col items-center justify-center p-6">
          {loading && <div className="text-zinc-400">Loading QR code...</div>}

          {error && (
            <div className="bg-red-900/50 border border-red-500 text-red-200 px-4 py-3 rounded mb-4">
              {error}
            </div>
          )}

          {qrCode && !loading && (
            <div className="bg-white p-4 rounded-lg">
              <img src={qrCode} alt="WhatsApp QR Code" className="w-64 h-64" />
            </div>
          )}

          {!qrCode && !loading && !error && (
            <div className="text-zinc-400">No QR code available</div>
          )}
        </div>

        <div className="flex justify-end gap-2">
          <Button variant="outline" onClick={loadQRCode} disabled={loading || !instanceName}>
            Refresh QR
          </Button>
          <Button onClick={() => onOpenChange(false)}>Close</Button>
        </div>
      </DialogContent>
    </Dialog>
  )
}
