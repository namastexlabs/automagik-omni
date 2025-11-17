import { useState, useEffect } from 'react'
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
import { Switch } from '@/app/components/ui/switch'
import { MessageSquareText } from 'lucide-react'
import { useConveyor } from '@/app/hooks/use-conveyor'
import type { Instance } from '@/lib/conveyor/schemas/omni-schema'

const editInstanceSchema = z.object({
  evolution_url: z.string().url('Must be a valid URL').optional().or(z.literal('')),
  evolution_key: z.string().optional(),
  discord_bot_token: z.string().optional(),
  discord_guild_id: z.string().optional(),
  agent_api_url: z.string().url('Must be a valid URL'),
  agent_api_key: z.string().optional(),
  agent_timeout: z.number().min(1).max(300).optional(),
  default_agent: z.string().optional(),
  enable_auto_split: z.boolean().optional(),
})

type EditInstanceFormData = z.infer<typeof editInstanceSchema>

interface EditInstanceDialogProps {
  instance: Instance | null
  open: boolean
  onOpenChange: (open: boolean) => void
  onUpdated: () => void
}

export function EditInstanceDialog({ instance, open, onOpenChange, onUpdated }: EditInstanceDialogProps) {
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
  } = useForm<EditInstanceFormData>({
    resolver: zodResolver(editInstanceSchema),
  })

  // Reset form when instance changes
  useEffect(() => {
    if (instance) {
      // Convert milliseconds to seconds for display
      const timeoutValue = instance.agent_timeout || 30000
      const timeoutSeconds = timeoutValue >= 1000 ? timeoutValue / 1000 : timeoutValue

      reset({
        evolution_url: instance.evolution_url || '',
        evolution_key: instance.evolution_key || '',
        discord_bot_token: instance.discord_bot_token || '',
        discord_guild_id: instance.discord_guild_id || '',
        agent_api_url: instance.agent_api_url || '',
        agent_api_key: instance.agent_api_key || '',
        agent_timeout: timeoutSeconds,
        default_agent: instance.default_agent || '',
        enable_auto_split: instance.enable_auto_split ?? true,
      })
    }
  }, [instance, reset])

  const onSubmit = async (data: EditInstanceFormData) => {
    if (!instance) return

    try {
      setLoading(true)
      setError(null)

      // Convert seconds to milliseconds for API
      const timeoutMs = (data.agent_timeout || 30) * 1000

      const payload: any = {
        agent_api_url: data.agent_api_url,
        agent_timeout: timeoutMs,
        enable_auto_split: data.enable_auto_split ?? true,
      }

      if (data.agent_api_key) {
        payload.agent_api_key = data.agent_api_key
      }

      if (data.default_agent) {
        payload.default_agent = data.default_agent
      }

      if (instance.channel_type === 'whatsapp') {
        if (data.evolution_url) payload.evolution_url = data.evolution_url
        if (data.evolution_key) payload.evolution_key = data.evolution_key
      } else if (instance.channel_type === 'discord') {
        if (data.discord_bot_token) payload.discord_bot_token = data.discord_bot_token
        if (data.discord_guild_id) payload.discord_guild_id = data.discord_guild_id
      }

      await omni.updateInstance(instance.name, payload)
      onUpdated()
      onOpenChange(false)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update instance')
    } finally {
      setLoading(false)
    }
  }

  if (!instance) return null

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Edit Instance: {instance.name}</DialogTitle>
          <DialogDescription>
            Update configuration for this {instance.channel_type} instance
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          {error && (
            <div className="bg-red-900/50 border border-red-500 text-red-200 px-4 py-3 rounded">
              {error}
            </div>
          )}

          <div className="space-y-2">
            <div className="flex items-center justify-between p-3 bg-zinc-800/50 border border-zinc-700 rounded-lg">
              <div>
                <Label className="text-sm text-zinc-400">Instance Name</Label>
                <p className="font-medium text-white">{instance.name}</p>
              </div>
              <div>
                <Label className="text-sm text-zinc-400">Channel Type</Label>
                <p className="font-medium text-white capitalize">{instance.channel_type}</p>
              </div>
            </div>
          </div>

          {instance.channel_type === 'whatsapp' && (
            <>
              <div className="space-y-2">
                <Label htmlFor="evolution_url">Evolution API URL</Label>
                <Input
                  id="evolution_url"
                  placeholder="https://evolution-api.example.com"
                  {...register('evolution_url')}
                  className="bg-zinc-800 border-zinc-700 text-white"
                />
                {errors.evolution_url && (
                  <p className="text-sm text-red-400">{errors.evolution_url.message}</p>
                )}
              </div>

              <div className="space-y-2">
                <Label htmlFor="evolution_key">Evolution API Key</Label>
                <Input
                  id="evolution_key"
                  type="password"
                  placeholder="Leave blank to keep existing"
                  {...register('evolution_key')}
                  className="bg-zinc-800 border-zinc-700 text-white"
                />
              </div>
            </>
          )}

          {instance.channel_type === 'discord' && (
            <>
              <div className="space-y-2">
                <Label htmlFor="discord_bot_token">Discord Bot Token</Label>
                <Input
                  id="discord_bot_token"
                  type="password"
                  placeholder="Leave blank to keep existing"
                  {...register('discord_bot_token')}
                  className="bg-zinc-800 border-zinc-700 text-white"
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="discord_guild_id">Discord Guild ID</Label>
                <Input
                  id="discord_guild_id"
                  placeholder="Guild ID"
                  {...register('discord_guild_id')}
                  className="bg-zinc-800 border-zinc-700 text-white"
                />
              </div>
            </>
          )}

          <div className="space-y-2">
            <Label htmlFor="agent_api_url">Agent API URL *</Label>
            <Input
              id="agent_api_url"
              placeholder="https://agent-api.example.com"
              {...register('agent_api_url')}
              className="bg-zinc-800 border-zinc-700 text-white"
            />
            {errors.agent_api_url && (
              <p className="text-sm text-red-400">{errors.agent_api_url.message}</p>
            )}
          </div>

          <div className="space-y-2">
            <Label htmlFor="agent_api_key">Agent API Key</Label>
            <Input
              id="agent_api_key"
              type="password"
              placeholder="Leave blank to keep existing"
              {...register('agent_api_key')}
              className="bg-zinc-800 border-zinc-700 text-white"
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="default_agent">Default Agent</Label>
            <Input
              id="default_agent"
              placeholder="agent-name"
              {...register('default_agent')}
              className="bg-zinc-800 border-zinc-700 text-white"
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="agent_timeout">Agent Timeout (seconds)</Label>
            <Input
              id="agent_timeout"
              type="number"
              placeholder="30"
              {...register('agent_timeout', { valueAsNumber: true })}
              className="bg-zinc-800 border-zinc-700 text-white"
            />
            {errors.agent_timeout ? (
              <p className="text-sm text-red-400">{errors.agent_timeout.message}</p>
            ) : (
              <p className="text-xs text-zinc-500">Timeout in seconds (1-300s)</p>
            )}
          </div>

          <div className="space-y-3 border border-zinc-700 rounded-lg p-4 bg-zinc-800/50">
            <div className="flex items-center justify-between gap-4">
              <div className="flex items-center gap-2">
                <MessageSquareText className="h-4 w-4 text-zinc-400" />
                <Label htmlFor="enable_auto_split" className="text-sm font-medium cursor-pointer">
                  Auto-split messages
                </Label>
              </div>
              <Switch
                id="enable_auto_split"
                checked={watch('enable_auto_split') ?? true}
                onCheckedChange={(checked) => setValue('enable_auto_split', checked)}
              />
            </div>
            <p className="text-xs text-zinc-400 leading-relaxed">
              Split long messages at paragraph breaks (double newline).
              <br />
              <span className="text-zinc-500">
                WhatsApp: Controls splitting behavior. Discord: Preferred split point (2000-char limit always applies).
              </span>
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
              {loading ? 'Updating...' : 'Update Instance'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
