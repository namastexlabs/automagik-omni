import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/app/components/ui/dialog'
import { Button } from '@/app/components/ui/button'
import { Input } from '@/app/components/ui/input'
import { Label } from '@/app/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/app/components/ui/select'
import { useConveyor } from '@/app/hooks/use-conveyor'
import type { Instance } from '@/lib/main/omni-api-client'

const createRuleSchema = z.object({
  phone_number: z
    .string()
    .min(1, 'Phone number is required')
    .regex(
      /^(\*|\+\d+\*?)$/,
      'Must be * (all numbers) or start with + followed by digits, optionally ending with *'
    ),
  rule_type: z.enum(['allow', 'block']),
  instance_name: z.string().optional(),
})

type CreateRuleFormData = z.infer<typeof createRuleSchema>

interface CreateRuleDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  onCreated: () => void
  instances: Instance[]
}

export function CreateRuleDialog({
  open,
  onOpenChange,
  onCreated,
  instances,
}: CreateRuleDialogProps) {
  const { omni } = useConveyor()
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const {
    register,
    handleSubmit,
    formState: { errors },
    reset,
    setValue,
    watch,
  } = useForm<CreateRuleFormData>({
    resolver: zodResolver(createRuleSchema),
    defaultValues: {
      rule_type: 'allow',
      instance_name: '',
    },
  })

  const ruleType = watch('rule_type')
  const instanceName = watch('instance_name')

  const onSubmit = async (data: CreateRuleFormData) => {
    try {
      setLoading(true)
      setError(null)

      // If instance_name is empty string, convert to undefined for global scope
      const payload = {
        ...data,
        instance_name: data.instance_name === '' ? undefined : data.instance_name,
      }

      // Create the rule via API
      await omni.createAccessRule(payload)

      reset()
      onCreated()
      onOpenChange(false)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create rule')
    } finally {
      setLoading(false)
    }
  }

  const handleRuleTypeChange = (value: string) => {
    setValue('rule_type', value as 'allow' | 'block')
  }

  const handleScopeChange = (value: string) => {
    setValue('instance_name', value === 'global' ? '' : value)
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Create Access Rule</DialogTitle>
          <DialogDescription>
            Add a new allow or block rule for phone numbers
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          {error && (
            <div className="bg-red-900/50 border border-red-500 text-red-200 px-4 py-3 rounded">
              {error}
            </div>
          )}

          <div className="space-y-2">
            <Label htmlFor="phone_number">Phone Number *</Label>
            <Input
              id="phone_number"
              placeholder="* or +1234567890 or +1*"
              {...register('phone_number')}
              className="bg-zinc-800 border-zinc-700 text-white"
            />
            {errors.phone_number && (
              <p className="text-sm text-red-400">{errors.phone_number.message}</p>
            )}
            <p className="text-xs text-zinc-400">
              Use * to match all numbers, or +1* for prefix matching (e.g., all US numbers)
            </p>
          </div>

          <div className="space-y-2">
            <Label htmlFor="rule_type">Rule Type *</Label>
            <Select value={ruleType} onValueChange={handleRuleTypeChange}>
              <SelectTrigger className="bg-zinc-800 border-zinc-700 text-white">
                <SelectValue placeholder="Select rule type" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="allow">Allow</SelectItem>
                <SelectItem value="block">Block</SelectItem>
              </SelectContent>
            </Select>
            {errors.rule_type && (
              <p className="text-sm text-red-400">{errors.rule_type.message}</p>
            )}
          </div>

          <div className="space-y-2">
            <Label htmlFor="instance_name">Scope</Label>
            <Select
              value={instanceName === '' ? 'global' : instanceName}
              onValueChange={handleScopeChange}
            >
              <SelectTrigger className="bg-zinc-800 border-zinc-700 text-white">
                <SelectValue placeholder="Select scope" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="global">Global (All Instances)</SelectItem>
                {instances.map((instance) => (
                  <SelectItem key={instance.name} value={instance.name}>
                    {instance.name} ({instance.channel_type})
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <p className="text-xs text-zinc-400">
              Global rules apply to all instances, or choose a specific instance
            </p>
          </div>

          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => onOpenChange(false)}
              disabled={loading}
            >
              Cancel
            </Button>
            <Button type="submit" disabled={loading}>
              {loading ? 'Creating...' : 'Create Rule'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
