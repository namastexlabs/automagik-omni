import { useState, useEffect, useRef } from 'react'
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
  const [connected, setConnected] = useState(false)
  const qrIntervalRef = useRef<NodeJS.Timeout | null>(null)
  const statusIntervalRef = useRef<NodeJS.Timeout | null>(null)

  useEffect(() => {
    if (open && instanceName) {
      loadQRCode()
      checkStatus() // Initial status check

      // Auto-refresh QR code every 30 seconds (in background)
      qrIntervalRef.current = setInterval(() => {
        loadQRCode(true) // Pass true to load silently
      }, 30000)

      // Check status every 3 seconds to detect connection
      statusIntervalRef.current = setInterval(checkStatus, 3000)
    }

    return () => {
      if (qrIntervalRef.current) clearInterval(qrIntervalRef.current)
      if (statusIntervalRef.current) clearInterval(statusIntervalRef.current)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, instanceName])

  const loadQRCode = async (silent = false) => {
    if (!instanceName) return

    try {
      if (!silent) setLoading(true)
      setError(null)
      const result = await omni.getInstanceQR(instanceName)
      // Backend returns base64 data URL (e.g., data:image/png;base64,...)
      const qrImageData = result.qr_code || result.base64
      setQrCode(qrImageData)
    } catch (err) {
      if (!silent) {
        setError(err instanceof Error ? err.message : 'Failed to load QR code')
      }
    } finally {
      if (!silent) setLoading(false)
    }
  }

  const checkStatus = async () => {
    if (!instanceName) return

    try {
      const status = await omni.getInstanceStatus(instanceName)
      if (status.connected || status.status === 'connected') {
        setConnected(true)
        // Auto-close after a brief delay to show success
        setTimeout(() => {
          onOpenChange(false)
          setConnected(false)
          setQrCode(null)
        }, 1500)
      }
    } catch (err) {
      // Silently fail - status checks are background operations
      console.debug('Status check failed:', err)
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
          {connected && (
            <div className="bg-green-900/50 border border-green-500 text-green-200 px-4 py-3 rounded mb-4">
              ✓ Connected successfully! Closing...
            </div>
          )}

          {!connected && loading && <div className="text-zinc-400">Loading QR code...</div>}

          {!connected && error && (
            <div className="bg-red-900/50 border border-red-500 text-red-200 px-4 py-3 rounded mb-4">
              {error}
            </div>
          )}

          {!connected && qrCode && !loading && (
            <div className="bg-white p-4 rounded-lg">
              <img src={qrCode} alt="WhatsApp QR Code" className="w-64 h-64" />
              <p className="text-center text-sm text-zinc-600 mt-2">
                Checking connection status...
              </p>
            </div>
          )}

          {!connected && !qrCode && !loading && !error && (
            <div className="text-zinc-400">No QR code available</div>
          )}
        </div>

        <div className="flex justify-end gap-2">
          <Button
            variant="outline"
            onClick={() => loadQRCode()}
            disabled={loading || connected || !instanceName}
          >
            Refresh QR
          </Button>
          <Button onClick={() => onOpenChange(false)} disabled={connected}>
            Close
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  )
}
