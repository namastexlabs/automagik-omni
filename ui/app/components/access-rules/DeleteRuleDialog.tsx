import { useState } from 'react'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/app/components/ui/dialog'
import { Button } from '@/app/components/ui/button'

interface DeleteRuleDialogProps {
  ruleId: number | null
  phoneNumber: string | null
  open: boolean
  onOpenChange: (open: boolean) => void
  onDeleted: () => void
  onDelete: (ruleId: number) => Promise<void>
}

export function DeleteRuleDialog({
  ruleId,
  phoneNumber,
  open,
  onOpenChange,
  onDeleted,
  onDelete,
}: DeleteRuleDialogProps) {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleDelete = async () => {
    if (!ruleId) return

    try {
      setLoading(true)
      setError(null)
      await onDelete(ruleId)
      onDeleted()
      onOpenChange(false)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete rule')
    } finally {
      setLoading(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Delete Access Rule</DialogTitle>
          <DialogDescription>
            Are you sure you want to delete the rule for "{phoneNumber}"?
          </DialogDescription>
        </DialogHeader>

        <div className="bg-red-900/20 border border-red-500/50 text-red-200 px-4 py-3 rounded">
          <p className="text-sm font-medium">This action cannot be undone</p>
        </div>

        {error && (
          <div className="bg-red-900/50 border border-red-500 text-red-200 px-4 py-3 rounded">
            {error}
          </div>
        )}

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={loading}>
            Cancel
          </Button>
          <Button variant="destructive" onClick={handleDelete} disabled={loading || !ruleId}>
            {loading ? 'Deleting...' : 'Delete'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
