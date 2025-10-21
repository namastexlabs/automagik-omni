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
import { useConveyor } from '@/app/hooks/use-conveyor'
import type { AccessRule } from './AccessRulesTable'

interface DeleteRuleDialogProps {
  rule: AccessRule | null
  open: boolean
  onOpenChange: (open: boolean) => void
  onDeleted: () => void
}

export function DeleteRuleDialog({
  rule,
  open,
  onOpenChange,
  onDeleted,
}: DeleteRuleDialogProps) {
  const { omni } = useConveyor()
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleDelete = async () => {
    if (!rule) return

    try {
      setLoading(true)
      setError(null)
      await omni.deleteAccessRule(rule.id)
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
            Are you sure you want to delete the rule for "{rule?.phone_number}"?
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
          <Button variant="destructive" onClick={handleDelete} disabled={loading || !rule}>
            {loading ? 'Deleting...' : 'Delete'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
